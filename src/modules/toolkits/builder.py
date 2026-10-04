import inspect
from typing import get_type_hints

from pydantic import TypeAdapter

from modules.toolkits.models import Tool, ToolBlueprint, ToolKit


def build_tool(kit_name: str, blueprint: ToolBlueprint) -> Tool:
    """Returns a Tool class that holds the schema, description, and the live object function of the tool"""
    func = blueprint.func
    ignore = set(blueprint.params_to_ignore)

    sig = inspect.signature(func)
    hints = get_type_hints(func)

    properties: dict[str, object] = {}
    required: list[str] = []

    # Checks each parameter for the function to check required/optional params
    # Skips self and cls named params
    for name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if name in ("self", "cls") or name in ignore:
            continue

        properties[name] = TypeAdapter(hints.get(name, str)).json_schema()

        if param.default is inspect.Parameter.empty:
            required.append(name)

    return Tool(
        kit_name=kit_name,
        name=func.__name__,
        func=func,
        param_names=frozenset(properties),
        required=required,
        tool_schema={
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": inspect.getdoc(func) or "",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        },
    )


def build_toolkit(
    name: str,
    desc: str,
    instructions: str,
    blueprints: list[ToolBlueprint],
    core: bool = False,
) -> ToolKit:
    """Builds a toolkit using the given blueprints"""
    tools = {bp.func.__name__: build_tool(name, bp) for bp in blueprints}
    return ToolKit(
        name=name, desc=desc, tools=tools, instructions=instructions, core=core
    )
