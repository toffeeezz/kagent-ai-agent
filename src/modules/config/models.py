from dataclasses import dataclass
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict


class TextAgentConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    system_prompt_path: str
    temperature: float = 0.7
    top_p: float = 1.0
    max_completion_tokens: int | None = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    seed: int | None = None
    stop: list[str] | None = None
    response_format: dict[str, object] | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None


class EmbeddingAgentConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    dimensions: int | None = None
    encoding_format: Literal["float", "base64"] = "float"
