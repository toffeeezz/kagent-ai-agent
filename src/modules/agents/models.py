import base64
import copy
import json
import logging
import mimetypes
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Literal, cast, override

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL
from pydantic import BaseModel, ConfigDict, Field, model_validator

from modules.agents.errors import AgentError
from modules.server.models import LLMParams, LLMPayload, LLMResponse
from modules.server.server import Server
from modules.toolkits.errors import ToolExecutionError
from modules.toolkits.models import ToolResult
from modules.toolkits.registry import ToolkitRegistry

logger = logging.getLogger(__name__)

ImageSource = str | Path | bytes
Detail = Literal["auto", "low", "high"]

RUN_ERROR_TOOL = "run_error"

SAY_LOG_LIMIT = 1000


def image_part(
    source: ImageSource,
    mime: str = "image/png",
    detail: Detail | None = None,
) -> ChatCompletionContentPartImageParam:
    if isinstance(source, Path):
        mime = mimetypes.guess_type(source.name)[0] or mime
        url = f"data:{mime};base64,{base64.b64encode(source.read_bytes()).decode()}"
    elif isinstance(source, bytes):
        url = f"data:{mime};base64,{base64.b64encode(source).decode()}"
    else:
        url = source

    image_url: ImageURL = {"url": url}
    if detail is not None:
        image_url["detail"] = detail
    return {"type": "image_url", "image_url": image_url}


def _preview(text: str | None, limit: int = 200) -> str:
    """Single-line, truncated text for logs."""
    flat = " ".join((text or "").split())
    return (
        flat
        if len(flat) <= limit
        else f"{flat[:limit]}... (+{len(flat) - limit} chars)"
    )


def _log_say(speaker: str, text: str, images: int = 0) -> None:
    """Log something a user or the agent said. Full text at DEBUG."""
    logger.info(
        "Say: [%s] %s%s",
        speaker,
        _preview(text, SAY_LOG_LIMIT),
        f" (+{images} image(s))" if images else "",
    )
    logger.debug("Say (full): [%s] %s", speaker, text)


def _user_message(
    text: str, images: Sequence[ImageSource] = ()
) -> ChatCompletionUserMessageParam:
    """Plain user message, no speaker tag."""
    if not images:
        return {"role": "user", "content": text}
    parts: list[ChatCompletionContentPartParam] = [{"type": "text", "text": text}]
    parts.extend(image_part(img) for img in images)
    return {"role": "user", "content": parts}


def _tagged_user_message(
    name: str, text: str, images: Sequence[ImageSource] = ()
) -> ChatCompletionUserMessageParam:
    """'John' + 'hi' -> '[User John]: hi'."""
    return _user_message(f"[User {name}]: {text}", images)


class BaseAgent(ABC):
    """Owns config and the generate flow. Subclasses decide how a user
    message becomes a payload (and whether history is kept)."""

    name: str
    _language_model: str
    _system_prompt: str
    _params: LLMParams

    def __init__(
        self, name: str, language_model: str, system_prompt: str, params: LLMParams
    ) -> None:
        self.name = name
        self._language_model = language_model
        self._system_prompt = system_prompt
        self._params = params
        logger.info(
            "Agent ready: type=%s name=%s model=%s system_prompt_chars=%d",
            type(self).__name__,
            name,
            language_model,
            len(system_prompt),
        )

    async def generate(
        self,
        server: Server,
        username: str,
        input: str,
        images: Sequence[ImageSource] | None = None,
    ) -> LLMResponse:
        logger.info(
            "Prompt: agent=%s model=%s images=%d input=%s",
            self.name,
            self._language_model,
            len(images or []),
            _preview(input),
        )
        user_message = self._build_user_message(input, username, images)
        payload = self._build_payload(user_message)
        try:
            response = await server.send_request_llm(payload)
        except Exception:
            logger.exception("Request failed: agent=%s", self.name)
            raise
        logger.info(
            "Reply: agent=%s finish_reason=%s cost=$%.8f content=%s",
            self.name,
            response.finish_reason,
            response.total_cost,
            _preview(response.content, SAY_LOG_LIMIT),
        )
        return response

    def _build_user_message(
        self, text: str, name: str, images: Sequence[ImageSource] | None = None
    ) -> ChatCompletionUserMessageParam:
        """Default: tagged as '[User <name>]: text'."""
        return _tagged_user_message(name, text, images or ())

    @abstractmethod
    def _build_payload(
        self, user_message: ChatCompletionUserMessageParam
    ) -> LLMPayload: ...


class BasicAgent(BaseAgent):
    """Stateless one-shot helper (summarizer, etc.): every call is a fresh
    [system, user] exchange. No speaker tag on the input; `username` is
    accepted for interface compatibility but ignored."""

    @override
    def _build_user_message(
        self, text: str, name: str, images: Sequence[ImageSource] | None = None
    ) -> ChatCompletionUserMessageParam:
        return _user_message(text, images or ())

    @override
    def _build_payload(
        self, user_message: ChatCompletionUserMessageParam
    ) -> LLMPayload:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._system_prompt},
            user_message,
        ]
        return LLMPayload(
            agent_name=self.name,
            model=self._language_model,
            messages=messages,
            params=self._params,
        )


class CompleteAgent(BaseAgent):
    """Stateful: keeps its own message history and exposes tools.

    Pass the plain username ("John"); the agent sees it as "[User John]: ...".
    Each agent is fully isolated: it only ever sees its own messages.
    """

    _registry: ToolkitRegistry
    _messages: list[ChatCompletionMessageParam]
    _max_loops: int = 40

    def __init__(
        self,
        name: str,
        language_model: str,
        system_prompt: str,
        params: LLMParams,
        registry: ToolkitRegistry,
        max_loops: int = 40,
    ) -> None:
        super().__init__(name, language_model, system_prompt, params)
        self._registry = registry
        self._max_loops = max_loops
        self._messages = [{"role": "system", "content": self._system_prompt}]

    def reset(self) -> None:
        """Forget the conversation. Keeps the system prompt."""
        self._messages = [{"role": "system", "content": self._system_prompt}]
        logger.info("History reset: agent=%s", self.name)

    async def run(
        self,
        server: Server,
        username: str,
        input: str,
        images: Sequence[ImageSource] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> AsyncIterator[LLMResponse]:
        """Yields one LLMResponse per loop. The last one has no tool calls. This is used for the UI.

        If the run fails, the error is recorded in this agent's history as a
        tool message and then re-raised.
        """
        user_message = self._build_user_message(input, username, images)
        self._messages.append(user_message)
        _log_say(f"User {username}", input, len(images or []))

        logger.info(
            "Run start: agent=%s model=%s history=%d images=%d max_loops=%d",
            self.name,
            self._language_model,
            len(self._messages),
            len(images or []),
            self._max_loops,
        )
        total_cost = 0.0
        finished = False

        try:
            for loop in range(1, self._max_loops + 1):
                payload = self._build_payload(user_message, tool_choice)
                logger.info(
                    "Loop %d/%d start: agent=%s messages=%d tools=%d tool_choice=%s",
                    loop,
                    self._max_loops,
                    self.name,
                    len(payload.messages),
                    len(self._registry.schemas),
                    tool_choice or "auto",
                )
                response = await server.send_request_llm(payload)
                self._messages.append(self._to_assistant_param(response))
                total_cost += response.total_cost

                tool_names = [
                    tc.function.name
                    for tc in response.tool_calls
                    if tc.type == "function"
                ]
                logger.info(
                    "Loop %d/%d response: agent=%s finish_reason=%s tools=%s cost=$%.8f reasoning=%s",
                    loop,
                    self._max_loops,
                    self.name,
                    response.finish_reason,
                    tool_names,
                    response.total_cost,
                    _preview(response.reasoning),
                )

                if not response.tool_calls:
                    finished = True
                    if response.content and response.content.strip():
                        _log_say(f"Agent {self.name}", response.content)
                    else:
                        logger.warning(
                            "Empty final reply: agent=%s finish_reason=%s",
                            self.name,
                            response.finish_reason,
                        )
                    logger.info(
                        "Run complete: agent=%s loops=%d total_cost=$%.8f",
                        self.name,
                        loop,
                        total_cost,
                    )
                    yield response
                    return

                await self._run_tools(response)
                yield response

                tool_choice = None

            raise AgentError(f"{self.name} exceeded max iterations", self.name)
        except Exception as e:
            if not finished:
                logger.exception(
                    "Run failed: agent=%s total_cost=$%.8f", self.name, total_cost
                )
                self._record_failure(e)
            raise

    @override
    async def generate(
        self,
        server: Server,
        username: str,
        input: str,
        images: Sequence[ImageSource] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> LLMResponse:
        """Drains run() and returns the final response."""
        last: LLMResponse | None = None
        async for last in self.run(server, username, input, images, tool_choice):
            pass
        if last is None:
            raise AgentError(f"{self.name} produced no response", self.name)
        return last

    def _pending_tool_call_ids(self) -> list[str]:
        """Tool calls in the history that never got a tool message."""
        requested: list[str] = []
        answered: set[str] = set()
        for m in self._messages:
            if m["role"] == "assistant":
                requested.extend(tc["id"] for tc in m.get("tool_calls", []))
            elif m["role"] == "tool":
                answered.add(m["tool_call_id"])
        return [call_id for call_id in requested if call_id not in answered]

    def _record_failure(self, error: Exception) -> None:
        """Write the failure into the history as a tool message so the agent
        knows what happened on its next turn.

        A tool message must answer a tool call, so:
          - if the run died with tool calls still unanswered, answer them
            with the error;
          - otherwise (LLM request failed, max loops, ...) add a synthetic
            `run_error` tool call and answer it with the error.
        """
        content = ToolResult[None](
            ok=False,
            message=f"Run failed with {type(error).__name__}: {error}",
        ).to_content()

        pending = self._pending_tool_call_ids()
        logger.warning(
            "Recording failure: agent=%s error=%s unanswered_tool_calls=%d synthetic_call=%s",
            self.name,
            type(error).__name__,
            len(pending),
            not pending,
        )
        if not pending:
            call_id = f"{RUN_ERROR_TOOL}_{uuid.uuid4().hex[:8]}"
            self._messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": RUN_ERROR_TOOL, "arguments": "{}"},
                        }
                    ],
                }
            )
            pending = [call_id]

        for call_id in pending:
            self._messages.append(
                {"role": "tool", "tool_call_id": call_id, "content": content}
            )

    async def _run_tools(self, response: LLMResponse) -> None:
        for tc in response.tool_calls:
            if tc.type != "function":
                logger.warning(
                    "Skipping non-function tool call: agent=%s type=%s id=%s",
                    self.name,
                    tc.type,
                    tc.id,
                )
                continue
            content = await self._execute_tool(tc.function.name, tc.function.arguments)
            tool_message: ChatCompletionToolMessageParam = {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": content,
            }
            self._messages.append(tool_message)

    async def _execute_tool(self, name: str, raw_args: str) -> str:
        """Always returns tool-message content. Failures become ok=False
        results so the model can see them and retry."""
        try:
            parsed = json.loads(raw_args or "{}")
            if not isinstance(parsed, dict):
                raise TypeError("arguments must be a JSON object")
            kwargs = cast(dict[str, object], parsed)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                "Bad tool arguments: agent=%s tool=%s err=%s", self.name, name, e
            )
            return ToolResult[None](
                ok=False, message=f"Invalid arguments: {e}"
            ).to_content()

        logger.info(
            "Tool call: agent=%s tool=%s args=%s", self.name, name, _preview(raw_args)
        )
        started = time.perf_counter()
        try:
            result = await self._registry.execute_tool(self.name, name, kwargs)
        except ToolExecutionError as e:
            logger.warning(
                "Tool failed: agent=%s tool=%s elapsed=%.2fs err=%s",
                self.name,
                name,
                time.perf_counter() - started,
                e,
            )
            return ToolResult[None](ok=False, message=str(e)).to_content()
        except Exception as e:
            logger.exception(
                "Tool crashed: agent=%s tool=%s elapsed=%.2fs",
                self.name,
                name,
                time.perf_counter() - started,
            )
            return ToolResult[None](
                ok=False, message=f"Tool crashed with {type(e).__name__}: {e}"
            ).to_content()

        content = result.to_content()
        logger.info(
            "Tool result: agent=%s tool=%s ok=%s elapsed=%.2fs result=%s",
            self.name,
            name,
            result.ok,
            time.perf_counter() - started,
            _preview(content),
        )
        return content

    def _to_assistant_param(
        self, response: LLMResponse
    ) -> ChatCompletionAssistantMessageParam:
        msg = response.message
        param: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": msg.content or "",
        }
        if msg.tool_calls:
            param["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
                if tc.type == "function"
            ]
        return param

    @override
    def _build_payload(
        self,
        user_message: ChatCompletionUserMessageParam,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> LLMPayload:
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": f"{self._system_prompt}\n{self._registry.skills}",
        }

        return LLMPayload(
            agent_name=self.name,
            model=self._language_model,
            messages=[system_message, *self._messages[1:]],
            params=self._params,
            tools=self._registry.schemas,
            tool_choice=tool_choice or "auto",
        )


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: Literal["basic", "complete"]
    language_model: str
    max_loop: int | None = None
    params: LLMParams = Field(default_factory=LLMParams)

    @model_validator(mode="after")
    def check_max_loop(self):
        if self.type == "basic" and "max_loop" in self.model_fields_set:
            raise ValueError("max_loop is only allowed for a 'complete' agent type")
        return self
