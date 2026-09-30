import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from openai.types.chat import ChatCompletionToolUnionParam
from pydantic import BaseModel

T = TypeVar("T")

TOOL_NAME_RGX = r"^[a-zA-Z0-9_-]+$"


@dataclass
class ToolBlueprint:
    func: Callable[..., object]
    params_to_ignore: list[str] = field(default_factory=list)


@dataclass
class Tool:
    kit_name: str
    name: str
    func: Callable[..., object]
    tool_schema: ChatCompletionToolUnionParam
    param_names: frozenset[str]
    required: list[str]


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ToolKit:
    name: str
    desc: str
    instructions: str
    tools: dict[str, Tool]
    core: bool = False


@dataclass
class ToolResult(Generic[T]):
    ok: bool
    message: str
    data: T | None = None
    expose_data: bool = True

    def to_content(self) -> str:
        payload: dict[str, object] = {"ok": self.ok, "message": self.message}
        if self.expose_data:
            payload["data"] = self.data
        return json.dumps(payload)


class ToolCallEvent(BaseModel):
    tool_name: str
    kwargs: dict[str, object]


class ToolResultEvent(BaseModel):
    tool_name: str
    result: ToolResult[Any]
