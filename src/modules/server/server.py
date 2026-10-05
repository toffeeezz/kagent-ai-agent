import logging

from openai import (
    AsyncOpenAI,
    AsyncStream,
    OpenAIError,
)
from openai.types import CreateEmbeddingResponse, EmbeddingCreateParams
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
)
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsNonStreaming,
    CompletionCreateParamsStreaming,
)

from modules.server.errors import (
    EmbeddingRequestError,
    LLMRequestError,
)
from modules.server.models import (
    CustomEmbedding,
    EmbeddingPayload,
    EmbeddingResponse,
    FinishReason,
    LLMPayload,
    LLMResponse,
    OpenRouterUsage,
)

logger = logging.getLogger(__name__)


class Server:
    client: AsyncOpenAI

    def __init__(self, client: AsyncOpenAI) -> None:
        self.client = client

    async def send_request_embedding(self, payload: EmbeddingPayload):
        logger.debug(
            "Embedding request: agent=%s model=%s input_len=%d",
            payload.agent_name,
            payload.model,
            len(payload.input) if isinstance(payload.input, list) else 1,
        )

        results = await self._request_embedding(
            self.client,
            agent_name=payload.agent_name,
            params={"model": payload.model, "input": payload.input},
        )

        completion_usage = results.usage
        provider = getattr(results, "provider", "")
        usage = OpenRouterUsage.model_validate(completion_usage.model_dump())
        total_cost = usage.cost

        logger.info(
            "Embedding response: agent=%s model=%s provider=%s cost=$%.8f",
            payload.agent_name,
            payload.model,
            provider,
            total_cost,
        )

        response = self._parse_embedding_result(payload.input, results)
        response.provider = provider
        response.usage = usage
        response.total_cost = total_cost

        return response

    def _parse_embedding_result(
        self, input: list[str] | str, results: CreateEmbeddingResponse
    ) -> EmbeddingResponse:
        embeddings: list[CustomEmbedding] = []
        embedding: CustomEmbedding

        if isinstance(input, list):
            sorted_results = sorted(results.data, key=lambda d: d.index)
            for result in sorted_results:
                embedding = CustomEmbedding(
                    text=input[result.index], vectors=result.embedding
                )
                embeddings.append(embedding)
        else:
            embedding = CustomEmbedding(text=input, vectors=results.data[0].embedding)
            embeddings.append(embedding)

        return EmbeddingResponse(embeddings=embeddings)

    async def send_request_llm(self, payload: LLMPayload) -> LLMResponse:
        logger.debug(
            "LLM request: agent=%s model=%s messages=%d tools=%d",
            payload.agent_name,
            payload.model,
            len(payload.messages),
            len(payload.tools),
        )
        p = payload.params
        params: CompletionCreateParamsNonStreaming = {
            "model": payload.model,
            "messages": payload.messages,
            "tools": payload.tools,
            "tool_choice": payload.tool_choice,
            "stream": False,
        }
        optional: dict[str, object] = {
            "max_completion_tokens": p.max_completion_tokens,
            "reasoning_effort": p.reasoning_effort,
            "temperature": p.temperature,
            "top_p": p.top_p,
            "frequency_penalty": p.frequency_penalty,
            "presence_penalty": p.presence_penalty,
            "seed": p.seed,
            "stop": p.stop,
            "response_format": p.response_format,
        }
        params.update({k: v for k, v in optional.items() if v is not None})  # pyright: ignore[reportCallIssue, reportArgumentType]
        result = await self._request_llm_non_streaming(
            self.client, payload.agent_name, params=params
        )

        choices = result.choices[0]
        message = choices.message
        content = message.content or ""
        finish_reason = choices.finish_reason
        tool_calls = message.tool_calls or []
        extra = message.model_extra or {}
        reasoning = extra.get("reasoning") or ""
        reasoning_details = extra.get("reasoning_details")
        completion_usage = result.usage
        total_cost: float = 0
        provider = getattr(result, "provider", "")
        usage: OpenRouterUsage | None = None
        if completion_usage is not None:
            usage = OpenRouterUsage.model_validate(completion_usage.model_dump())
            total_cost = usage.cost

        logger.info(
            "LLM response: agent=%s model=%s provider=%s finish_reason=%s cost=$%.8f tool_calls=%d",
            payload.agent_name,
            payload.model,
            provider,
            finish_reason,
            total_cost,
            len(tool_calls),
        )
        return LLMResponse(
            raw_response=result,
            message=message,
            content=content,
            reasoning=reasoning,
            reasoning_details=reasoning_details or [],
            tool_calls=tool_calls,
            finish_reason=FinishReason(finish_reason),
            usage=usage,
            total_cost=total_cost,
            provider=provider,
        )

    async def _request_embedding(
        self, openai_client: AsyncOpenAI, agent_name: str, params: EmbeddingCreateParams
    ) -> CreateEmbeddingResponse:
        try:
            embedding = await openai_client.embeddings.create(**params)
            return embedding
        except OpenAIError as e:
            logger.exception("Embedding request failed: agent=%s", agent_name)
            raise EmbeddingRequestError(agent_name, str(e)) from e

    async def _request_llm_non_streaming(
        self,
        openai_client: AsyncOpenAI,
        agent_name: str,
        params: CompletionCreateParamsNonStreaming,
    ) -> ChatCompletion:
        params["stream"] = False
        try:
            completion: ChatCompletion = await openai_client.chat.completions.create(
                **params, extra_body={"reasoning": {"enabled": True}}
            )
            return completion
        except OpenAIError as e:
            logger.exception("LLM request failed: agent=%s", agent_name)
            body = getattr(e, "body", None)
            err = body.get("error", body) if isinstance(body, dict) else None
            detail = err.get("message") if isinstance(err, dict) else None
            raise LLMRequestError(agent_name, detail or str(e)) from e

    async def _request_llm_streaming(
        self,
        openai_client: AsyncOpenAI,
        agent_name: str,
        params: CompletionCreateParamsStreaming,
    ) -> AsyncStream[ChatCompletionChunk]:
        params["stream"] = True
        try:
            completion: AsyncStream[
                ChatCompletionChunk
            ] = await openai_client.chat.completions.create(
                **params, extra_body={"reasoning": {"enabled": True}}
            )
            return completion
        except OpenAIError as e:
            logger.exception("LLM streaming request failed: agent=%s", agent_name)
            raise LLMRequestError(agent_name, str(e)) from e
