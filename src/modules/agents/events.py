from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratingResponse:
    """The model request is in flight."""


@dataclass(frozen=True)
class GenerationFinished:
    """One model response arrived (text and/or reasoning; may be empty)."""

    content: str
    reasoning: str | None = None


@dataclass(frozen=True)
class ToolCallStarted:
    call_id: str
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ToolCallFinished:
    call_id: str
    ok: bool
    summary: str


@dataclass(frozen=True)
class RunError:
    message: str


AgentEvent = (
    GeneratingResponse
    | GenerationFinished
    | ToolCallStarted
    | ToolCallFinished
    | RunError
)
