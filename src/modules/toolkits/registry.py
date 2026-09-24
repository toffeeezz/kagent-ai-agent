import asyncio
import functools
import inspect
import logging
import re
from collections.abc import Callable
from dataclasses import field
from typing import Any

from pydantic import TypeAdapter, ValidationError

from modules.toolkits.errors import ToolExecutionError, ToolKitNotFoundError
from modules.toolkits.models import TOOL_NAME_RGX, T, Tool, ToolKit, ToolResult

logger = logging.getLogger(__name__)


class ToolkitRegistry:
    _core_kits: dict[str, ToolKit] = field(default_factory=dict[str, ToolKit])
    _registered_kits: dict[str, ToolKit] = field(default_factory=dict[str, ToolKit])
    _available_kits: dict[str, ToolKit] = field(default_factory=dict[str, ToolKit])
    _tool_to_kit: dict[str, str] = field(default_factory=dict[str, str])

    def __init__(
        self, core_kits: dict[str, ToolKit], available_kits: dict[str, ToolKit]
    ) -> None:
        self._core_kits = core_kits
        self._available_kits = available_kits

    def register_kit(self, name: str) -> None:
        if name not in self._available_kits:
            logger.error("Tried to register an unknown kit: %s", name)
            raise ToolKitNotFoundError(kit_name=name)

        if name in self._registered_kits:
            logger.warning("Tried to register an already registered kit: %s", name)
            return

        toolkit = self._available_kits.pop(name)
        self._registered_kits[name] = toolkit

        for tool_name in toolkit.tools:
            self._tool_to_kit[tool_name] = name

    def unregister_kit(self, name: str) -> None:
        if name not in self._registered_kits:
            logger.warning("Tried to unregister an unregistered kit: %s", name)
            return

        if name in self._available_kits:
            logger.warning(
                "A possible duplicate kit for %s was found in the available kits. Aborting operation to unregister to avoid accidental overwrites",
                name,
            )
            return

        kit = self._registered_kits.pop(name)
        self._available_kits[name] = self._registered_kits.pop(name)
        self._available_kits[name] = kit

        for tool_name in kit.tools:
            del self._tool_to_kit[tool_name]

    async def execute_tool(
        self, tool_name: str, kwargs: dict[str, object]
    ) -> ToolResult[Any]:
        if not re.fullmatch(TOOL_NAME_RGX, tool_name):
            logger.warning(
                "Tried to execute a tool using an invalid name format: %s", tool_name
            )
            raise ToolExecutionError(f"Invalid tool name: {tool_name}", None, None)

        kit_name = self._tool_to_kit.get(tool_name)
        if kit_name is None:
            logger.warning("Tried to execute an unknown tool: %s", tool_name)
            raise ToolExecutionError(f"Unknown tool: {tool_name}", None, tool_name)

        kit = self._registered_kits[kit_name]
        tool = kit.tools[tool_name]

        missing_args, extra_args = self._check_kwargs(tool.func, kwargs)

        if len(missing_args) > 1:
            logger.warning(
                "Failed to execute %s from %s: Missing arguments %s",
                tool_name,
                kit_name,
                missing_args,
            )
            raise ToolExecutionError(
                f"Missing arguments: {missing_args}", kit_name, tool_name
            )
        if len(extra_args) > 1:
            logger.warning(
                "Failed to execute %s from %s: Unexpected arguments %x",
                tool_name,
                kit_name,
                extra_args,
            )
            raise ToolExecutionError(
                f"Unexpected arguments: {extra_args}", kit_name, tool_name
            )

        loop = asyncio.get_running_loop()
        try:
            if inspect.iscoroutinefunction(tool.func):
                result = await tool.func(**kwargs)
            else:
                result = await loop.run_in_executor(
                    None, functools.partial(tool.func, **kwargs)
                )
        except Exception as e:
            raise ToolExecutionError(
                f"Tool {tool.name!r} raised an exception: {e}",
                tool.kit_name,
                tool.name,
            ) from e

        tool_result = self._validate_result(result, tool)

        return tool_result

    def _validate_result(self, result: object, tool: Tool) -> ToolResult[Any]:
        try:
            _tool_result_adapter: TypeAdapter[ToolResult[Any]] = TypeAdapter(
                ToolResult[Any]
            )
            return _tool_result_adapter.validate_python(result)
        except ValidationError as e:
            raise ToolExecutionError(
                message=f"Tool {tool.name!r} returned an invalid ToolResult: {e}",
                kit_name=tool.kit_name,
                tool_name=tool.name,
            ) from e

    def _check_kwargs(
        self, func: Callable[..., object], kwargs: dict[str, object]
    ) -> tuple[list[str], list[str]]:
        sig = inspect.signature(func)
        valid_param_names: set[str] = set()
        missing_args: list[str] = []
        extra_args: list[str] = []

        for name, param in sig.parameters.items():
            if name in ("self", "cls"):
                continue
            if param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL):
                continue

            valid_param_names.add(name)

            if param.default is inspect.Parameter.empty and name not in kwargs:
                missing_args.append(name)

            extra_args = [key for key in kwargs if key not in valid_param_names]

        return missing_args, extra_args
