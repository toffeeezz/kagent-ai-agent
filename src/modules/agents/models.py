from typing import Literal, NotRequired, Protocol, TypedDict, Unpack

from openai.types.chat import (
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolUnionParam,
)

from modules.server.models import (
    EmbeddingPayload,
    EmbeddingResponse,
    LLMPayload,
    LLMResponse,
)
from modules.server.server import Server


class LanguageModel(Protocol):
    model_name: str

    async def generate_response(self, payload: LLMPayload) -> LLMResponse:
        """Executes the raw LLM payload constructed by the agent."""
        ...


class EmbeddingModel(Protocol):
    model_name: str

    async def generate_embedding(self, payload: EmbeddingPayload) -> EmbeddingResponse:
        """Executes the raw Embedding payload constructed by the agent."""
        ...


class LanguageModelAdapter:
    model_name: str
    _server: Server

    @property
    def server(self) -> Server:
        return self._server

    def __init__(self, server: Server, model_name: str) -> None:
        self._server = server
        self.model_name = model_name

    async def generate_response(self, payload: LLMPayload) -> LLMResponse:
        return await self._server.send_request_llm(payload)


class TextAgent(Protocol):
    name: str

    @property
    def model(self) -> LanguageModel: ...

    async def run(self, prompt: str) -> LLMResponse: ...


class EmbeddingAgent(Protocol):
    name: str

    @property
    def model(self) -> EmbeddingModel: ...

    async def run(self, input: str | list[str]) -> EmbeddingResponse: ...


class TextAgentKwargs(TypedDict):
    temperature: NotRequired[float]
    reasoning_effort: NotRequired[Literal["low", "medium", "high"] | None]
    max_completion_tokens: NotRequired[int | None]
    tools: NotRequired[list[ChatCompletionToolUnionParam]]
    tool_choice: NotRequired[ChatCompletionToolChoiceOptionParam]


class BaseTextAgent:
    name: str
    _model: LanguageModel
    _temperature: float
    _reasoning_effort: Literal["low", "medium", "high"] | None
    _max_completion_tokens: int | None
    _tools: list[ChatCompletionToolUnionParam]
    _tool_choice: ChatCompletionToolChoiceOptionParam

    def __init__(
        self, name: str, model: LanguageModel, **kwargs: Unpack[TextAgentKwargs]
    ) -> None:
        self.name = name
        self._model = model
        self._temperature = kwargs.get("temperature", 1.0)
        self._reasoning_effort = kwargs.get("reasoning_effort")
        self._max_completion_tokens = kwargs.get("max_completion_tokens")
        self._tools = kwargs.get("tools") or []
        self._tool_choice = kwargs.get("tool_choice", "auto")

    @property
    def model(self) -> LanguageModel:
        return self._model

    async def run(self, prompt: str) -> LLMResponse:
        payload = self._build_payload(prompt)
        return await self._model.generate_response(payload)

    def _build_payload(self, prompt: str) -> LLMPayload:
        return LLMPayload(
            agent_name=self.name,
            model=self._model.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self._temperature,
            reasoning_effort=self._reasoning_effort,
            max_completion_tokens=self._max_completion_tokens,
            tools=self._tools,
            tool_choice=self._tool_choice,
        )
