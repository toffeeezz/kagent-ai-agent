import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from openai.types.chat import ChatCompletionToolUnionParam

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


@dataclass
class ToolKit:
    name: str
    desc: str
    tools: dict[str, Tool]


@dataclass
class ToolResult(Generic[T]):
    ok: bool
    message: str
    data: T | None = None

    def to_content(self) -> str:
        """The message that gets sent back to the model"""

        return json.dumps({"ok": self.ok, "message": self.message, "data": self.data})
