from collections.abc import Iterable
from enum import StrEnum
from typing import Literal

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallUnion,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolUnionParam,
)
from pydantic import BaseModel, Field


class LLMParams(BaseModel):
    temperature: float = 1.0
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    seed: int | None = None
    stop: list[str] | None = None
    response_format: dict[str, object] | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    max_completion_tokens: int | None = None


class ServerPayload(BaseModel):
    agent_name: str
    model: str


class EmbeddingPayload(ServerPayload):
    input: str | Iterable[str]
    dimensions: int | None = None
    encoding_format: Literal["float", "base64"] | None = None


class LLMPayload(ServerPayload):
    messages: list[ChatCompletionMessageParam] = Field(default_factory=list)
    tools: list[ChatCompletionToolUnionParam] = Field(default_factory=list)
    tool_choice: ChatCompletionToolChoiceOptionParam = "auto"
    stream: bool = False
    params: LLMParams = LLMParams()


class OpenRouterUsage(BaseModel):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    cost: float
    cost_details: dict[str, float] | None = None


class FinishReason(StrEnum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    FUNCTION_CALL = "function_call"


class ReasoningDetail(BaseModel):
    type: str
    text: str
    format: str
    index: int


class CustomEmbedding(BaseModel):
    text: str
    vectors: list[float]


class LLMResponse(BaseModel):
    raw_response: ChatCompletion
    message: ChatCompletionMessage
    content: str = ""
    reasoning_details: list[ReasoningDetail] = Field(default_factory=list)
    reasoning: str = ""
    tool_calls: list[ChatCompletionMessageToolCallUnion] = Field(default_factory=list)
    finish_reason: FinishReason
    usage: OpenRouterUsage | None = None
    total_cost: float = 0
    provider: str = ""


class EmbeddingResponse(BaseModel):
    embeddings: list[CustomEmbedding] | CustomEmbedding
    usage: OpenRouterUsage | None = None
    total_cost: float = 0
    provider: str = ""


class OpenRouterAssistantMessageParam(ChatCompletionAssistantMessageParam):
    reasoning: str
    reasoning_details: list[ReasoningDetail]
