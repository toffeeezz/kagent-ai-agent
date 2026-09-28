import base64
import json
import logging
import mimetypes
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Literal, cast, override

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL

from modules.agents.errors import AgentError
from modules.server.models import LLMParams, LLMPayload, LLMResponse
from modules.server.server import Server
from modules.toolkits.errors import ToolExecutionError
from modules.toolkits.models import ToolResult
from modules.toolkits.registry import ToolkitRegistry

logger = logging.getLogger(__name__)

ImageSource = str | Path | bytes
Detail = Literal["auto", "low", "high"]


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

    async def generate(
        self,
        server: Server,
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
        user_message = self._build_user_message(input, images)
        payload = self._build_payload(user_message)
        return await server.send_request_llm(payload)

    def _build_user_message(
        self, text: str, images: Sequence[ImageSource] | None = None
    ) -> ChatCompletionUserMessageParam:
        if not images:
            return {"role": "user", "content": text}
        parts: list[ChatCompletionContentPartParam] = [{"type": "text", "text": text}]
        parts.extend(image_part(img) for img in images)
        return {"role": "user", "content": parts}

    @abstractmethod
    def _build_payload(
        self, user_message: ChatCompletionUserMessageParam
    ) -> LLMPayload: ...


class BasicAgent(BaseAgent):
    """Stateless: every call is a fresh [system, user] exchange."""

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
    """Stateful: keeps history and exposes tools."""

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
        self._messages = [{"role": "system", "content": system_prompt}]
        self._max_loops = max_loops

    async def run(
        self,
        server: Server,
        input: str,
        images: Sequence[ImageSource] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> AsyncIterator[LLMResponse]:
        """Yields one LLMResponse per loop. The last one has no tool calls."""
        user_message = self._build_user_message(input, images)
        self._messages.append(user_message)

        logger.info(
            "Run start: agent=%s model=%s history=%d images=%d max_loops=%d input=%s",
            self.name,
            self._language_model,
            len(self._messages),
            len(images or []),
            self._max_loops,
            _preview(input),
        )
        total_cost = 0.0

        for loop in range(1, self._max_loops + 1):
            logger.info(
                "Loop %d/%d start: agent=%s messages=%d tools=%d tool_choice=%s",
                loop,
                self._max_loops,
                self.name,
                len(self._messages),
                len(self._registry.schemas),
                tool_choice or "auto",
            )
            payload = self._build_payload(user_message, tool_choice)
            response = await server.send_request_llm(payload)
            self._messages.append(self._to_assistant_param(response))
            total_cost += response.total_cost

            tool_names = [
                tc.function.name for tc in response.tool_calls if tc.type == "function"
            ]
            logger.info(
                "Loop %d/%d response: agent=%s finish_reason=%s tools=%s "
                "cost=$%.8f content=%s",
                loop,
                self._max_loops,
                self.name,
                response.finish_reason,
                tool_names,
                response.total_cost,
                _preview(response.content),
            )

            if not response.tool_calls:
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

        logger.error(
            "Run aborted: agent=%s exceeded %d loops total_cost=$%.8f",
            self.name,
            self._max_loops,
            total_cost,
        )
        raise AgentError(f"{self.name} exceeded max iterations", self.name)

    @override
    async def generate(
        self,
        server: Server,
        input: str,
        images: Sequence[ImageSource] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> LLMResponse:
        """Drains run() and returns the final response."""
        last: LLMResponse | None = None
        async for last in self.run(server, input, images, tool_choice):
            pass
        if last is None:
            raise AgentError(f"{self.name} produced no response", self.name)
        return last

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

        try:
            result = await self._registry.execute_tool(self.name, name, kwargs)
        except ToolExecutionError as e:
            return ToolResult[None](ok=False, message=str(e)).to_content()

        return result.to_content()

    def _to_assistant_param(
        self, response: LLMResponse
    ) -> ChatCompletionAssistantMessageParam:
        msg = response.message
        param: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": msg.content,
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
        return LLMPayload(
            agent_name=self.name,
            model=self._language_model,
            messages=list(self._messages),
            params=self._params,
            tools=self._registry.schemas,
            tool_choice=tool_choice or "auto",
        )
