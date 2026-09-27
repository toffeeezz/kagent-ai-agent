import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterable
from typing import Generic, TypeVar, override

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionToolMessageParam,
)

from modules.agents.errors import AgentError
from modules.config.models import EmbeddingAgentConfig, TextAgentConfig
from modules.server.models import (
    EmbeddingPayload,
    EmbeddingResponse,
    FinishReason,
    LLMPayload,
    LLMResponse,
)
from modules.server.server import Server
from modules.toolkits.errors import ToolExecutionError
from modules.toolkits.models import ToolCallEvent, ToolResult, ToolResultEvent
from modules.toolkits.registry import ToolkitRegistry

ConfigT = TypeVar("ConfigT")
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")

logger = logging.getLogger(__name__)


class BaseAgent(ABC, Generic[InputT, ConfigT, OutputT]):
    name: str
    _server: Server

    def __init__(self, name: str, server: Server) -> None:
        self.name = name
        self._server = server

    @abstractmethod
    async def run(self, model: str, config: ConfigT, input_data: InputT) -> OutputT: ...


TextAgentInput = str | Iterable[ChatCompletionContentPartParam]
EmbeddingAgentInput = str | Iterable[str]
AgentStreamEvent = ToolCallEvent | ToolResultEvent | LLMResponse


class TextAgent(BaseAgent[TextAgentInput, TextAgentConfig, LLMResponse]):
    def _build_tool_catalog(self) -> str:
        """Override in ToolCallingTextAgent; plain TextAgent has no tools."""
        return ""

    @override
    async def run(
        self,
        model: str,
        config: TextAgentConfig,
        input_data: TextAgentInput,
        history: list[ChatCompletionMessageParam] | None = None,
    ) -> LLMResponse:
        messages: list[ChatCompletionMessageParam] = list(history) if history else []
        messages.append({"role": "user", "content": input_data})

        payload = await self._build_payload(model, config, messages)
        response = await self._server.send_request_llm(payload)
        return response

    async def _build_payload(
        self,
        model: str,
        config: TextAgentConfig,
        messages: list[ChatCompletionMessageParam],
    ) -> LLMPayload:
        payload = LLMPayload(
            agent_name=self.name,
            model=model,
            messages=messages,
            temperature=config.temperature,
            top_p=config.top_p,
            frequency_penalty=config.frequency_penalty,
            presence_penalty=config.presence_penalty,
            seed=config.seed,
            stop=config.stop,
            response_format=config.response_format,
            reasoning_effort=config.reasoning_effort,
            max_completion_tokens=config.max_completion_tokens,
        )
        return payload


class EmbeddingAgent(
    BaseAgent[EmbeddingAgentInput, EmbeddingAgentConfig, EmbeddingResponse]
):
    @override
    async def run(
        self, model: str, config: EmbeddingAgentConfig, input_data: EmbeddingAgentInput
    ) -> EmbeddingResponse:
        payload = await self._build_payload(model, config, input_data)
        response = await self._server.send_request_embedding(payload)
        return response

    async def _build_payload(
        self, model: str, config: EmbeddingAgentConfig, input_data: EmbeddingAgentInput
    ) -> EmbeddingPayload:
        payload = EmbeddingPayload(
            agent_name=self.name,
            model=model,
            input=input_data,
            dimensions=config.dimensions,
            encoding_format=config.encoding_format,
        )
        return payload


class ToolCallingTextAgent(TextAgent):
    """Text agent that can invoke tools via a ToolkitRegistry, with a call→execute→call loop."""

    tool_registry: ToolkitRegistry

    def __init__(
        self, name: str, server: Server, tool_registry: ToolkitRegistry
    ) -> None:
        super().__init__(name, server)
        self.tool_registry = tool_registry

    @override
    async def _build_payload(
        self,
        model: str,
        config: TextAgentConfig,
        messages: list[ChatCompletionMessageParam],
    ) -> LLMPayload:
        payload = await super()._build_payload(model, config, messages)
        payload.tools = self.tool_registry.schemas
        return payload

    @override
    def _build_tool_catalog(self) -> str:
        lines = ["## Available Tools"]
        for schema in self.tool_registry.schemas:
            if schema["type"] == "custom":
                logger.error("Agent %s found a custom-type tool in its kit", self.name)
                raise AgentError(
                    f"A custom type tool was found inside a kit from {self.name}",
                    self.name,
                )
            fn = schema["function"]
            lines.append(f"- **{fn['name']}**: {fn.get('description')}")
        logger.debug(
            "Agent %s built tool catalog with %d tools", self.name, len(lines) - 1
        )
        return "\n".join(lines)

    def _message_to_param(
        self, message: ChatCompletionMessage
    ) -> ChatCompletionAssistantMessageParam:
        param: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": message.content,
        }

        if message.tool_calls:
            param["tool_calls"] = []
            for tool_call in message.tool_calls:
                if tool_call.type != "function":
                    logger.warning(
                        "Agent %s tried to request a %s tool call",
                        self.name,
                        tool_call.type,
                    )
                    raise AgentError(
                        message=f"Model tried to request a {tool_call.type!r} tool call which is not yet implemented",
                        name=self.name,
                    )
                param["tool_calls"].append(
                    ChatCompletionMessageToolCallParam(
                        id=tool_call.id,
                        type="function",
                        function={
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    )
                )

        return param

    @override
    async def run(
        self,
        model: str,
        config: TextAgentConfig,
        input_data: TextAgentInput,
        history: list[ChatCompletionMessageParam] | None = None,
        max_loops: int = 40,
    ) -> LLMResponse:
        final: LLMResponse | None = None
        async for event in self.run_stream(
            model, config, input_data, history, max_loops
        ):
            if isinstance(event, LLMResponse):
                final = event
        assert final is not None, (
            "run_stream must always yield a final LLMResponse or raise"
        )
        return final

    async def run_stream(
        self,
        model: str,
        config: TextAgentConfig,
        input_data: TextAgentInput,
        history: list[ChatCompletionMessageParam] | None = None,
        max_loops: int = 40,
    ) -> AsyncGenerator[AgentStreamEvent, None]:
        messages: list[ChatCompletionMessageParam] = list(history) if history else []
        messages.append({"role": "user", "content": input_data})

        for _ in range(max_loops):
            payload = await self._build_payload(model, config, messages)
            response = await self._server.send_request_llm(payload)

            message = response.message
            messages.append(self._message_to_param(message))

            if response.finish_reason == FinishReason.STOP:
                yield response
                return

            if response.finish_reason == FinishReason.CONTENT_FILTER:
                logger.warning(
                    "Content was filtered and halted during generation of agent %s",
                    self.name,
                )
                raise AgentError(
                    message="The content was filtered during generation",
                    name=self.name,
                )

            if response.finish_reason == FinishReason.LENGTH:
                logger.warning(
                    "Content exceeded max token length during generation of agent %s",
                    self.name,
                )
                raise AgentError(
                    message="The content exceeded max token length",
                    name=self.name,
                )

            if response.finish_reason in (
                FinishReason.TOOL_CALLS,
                FinishReason.FUNCTION_CALL,
            ):
                tool_msgs: list[ChatCompletionToolMessageParam] = []
                for tool_call in response.tool_calls:
                    if tool_call.type != "function":
                        logger.warning(
                            "Agent %s tried to execute a %s tool call",
                            self.name,
                            tool_call.type,
                        )
                        raise AgentError(
                            message=f"Tool call type {tool_call.type!r} is not yet implemented",
                            name=self.name,
                        )
                    try:
                        kwargs = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "Agent %s received malformed tool arguments for %s",
                            self.name,
                            tool_call.function.name,
                        )
                        raise ToolExecutionError(
                            message=f"Model produced invalid JSON arguments for tool {tool_call.function.name!r}: {e}",
                            kit_name=None,
                            tool_name=tool_call.function.name,
                        ) from e

                    yield ToolCallEvent(
                        tool_name=tool_call.function.name, kwargs=kwargs
                    )
                    try:
                        result = await self.tool_registry.execute_tool(
                            agent_name=self.name,
                            tool_name=tool_call.function.name,
                            kwargs=kwargs,
                        )
                    except ToolExecutionError as e:
                        result: ToolResult[str] = ToolResult(
                            ok=False,
                            message=f"An exception occured while executing the toot: {e}",
                        )
                    yield ToolResultEvent(
                        tool_name=tool_call.function.name, result=result
                    )

                    tool_msgs.append(
                        {
                            "role": "tool",
                            "content": result.to_content(),
                            "tool_call_id": tool_call.id,
                        }
                    )

                messages.extend(tool_msgs)
                continue

            raise AgentError(
                message=f"Unexpected finish reason: {response.finish_reason}",
                name=self.name,
            )

        logger.warning("Agent %s exceeded max loop count", self.name)
        raise AgentError(
            message=f"Agent {self.name} exceeded max loop count", name=self.name
        )
