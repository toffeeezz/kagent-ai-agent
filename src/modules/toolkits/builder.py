import inspect
from collections.abc import Callable
from typing import get_type_hints

from pydantic import TypeAdapter

from modules.toolkits.models import Tool, ToolBlueprint, ToolKit


def _build_tool(kit_name: str, blueprints: list[ToolBlueprint]) -> dict[str, Tool]:
    tool: dict[str, Tool] = {}

    for blueprint in blueprints:
        func = blueprint.func
        ignore_param_list = blueprint.params_to_ignore or []

        sig = inspect.signature(func)
        hints = get_type_hints(func)

        properties: dict[str, object] = {}
        required: list[str] = []

        for name, param in sig.parameters.items():
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            if name in ("self", "cls") or name in ignore_param_list:
                continue

            param_type = hints.get(name, str)
            properties[name] = TypeAdapter(param_type).json_schema()

            if param.default is inspect.Parameter.empty:
                required.append(name)

        tool[func.__name__] = Tool(
            name=func.__name__,
            kit_name=kit_name,
            func=func,
            tool_schema={
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": func.__doc__ or "",
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                        "additionalProperties": False,
                    },
                },
            },
        )

    return tool


def build_toolkit(name: str, desc: str, blueprints: list[ToolBlueprint]) -> ToolKit:
    tools = _build_tool(name, blueprints)
    return ToolKit(name=name, desc=desc, tools=tools)
