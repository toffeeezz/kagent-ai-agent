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


class ServerPayload(BaseModel):
    agent_name: str
    model: str


class EmbeddingPayload(ServerPayload):
    input: str | list[str]
    dimensions: int | None = None
    encoding_format: Literal["float", "base64"] | None = None


class LLMPayload(ServerPayload):
    messages: list[ChatCompletionMessageParam] = Field(default_factory=list)
    temperature: float = 1.0
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    max_completion_tokens: int | None = None
    tools: list[ChatCompletionToolUnionParam] = Field(default_factory=list)
    tool_choice: ChatCompletionToolChoiceOptionParam = "auto"
    stream: bool = False


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
    message: ChatCompletionMessage | None = None
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
