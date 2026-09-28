import asyncio
import functools
import inspect
import logging
import re
from typing import Any

from openai.types.chat import ChatCompletionToolUnionParam

from modules.toolkits.builder import build_toolkit
from modules.toolkits.errors import ToolExecutionError, ToolKitError
from modules.toolkits.models import (
    TOOL_NAME_RGX,
    Tool,
    ToolBlueprint,
    ToolKit,
    ToolResult,
)
from modules.toolkits.scanner import scan_toolkit_dir

logger = logging.getLogger(__name__)


class ToolkitRegistry:
    def __init__(self, kits: list[ToolKit] | None = None) -> None:
        self._core_kits: dict[str, ToolKit] = {}
        self._registered_kits: dict[str, ToolKit] = {}  # includes core kits
        self._available_kits: dict[str, ToolKit] = {}
        self._tool_to_kit: dict[str, str] = {}

        # the registry's own kit, built from its bound methods
        registry_kit = build_toolkit(
            "registry",
            "Tools for finding and enabling other toolkits",
            [
                ToolBlueprint(func=self.register_kit),
                ToolBlueprint(func=self.list_kits),
            ],
            core=True,
        )

        all_kits = [registry_kit, *(kits or [])]
        self._check_unique(all_kits)

        # core kits start active, everything else waits in available
        for kit in all_kits:
            if kit.core:
                self._core_kits[kit.name] = kit
                self._registered_kits[kit.name] = kit
                self._index_tools(kit)
            else:
                self._available_kits[kit.name] = kit

        logger.info(
            "Registry ready: core=%s available=%s",
            sorted(self._core_kits),
            sorted(self._available_kits),
        )

    @property
    def schemas(self) -> list[ChatCompletionToolUnionParam]:
        return [
            tool.tool_schema
            for kit in self._registered_kits.values()
            for tool in kit.tools.values()
        ]

    @property
    def available_kits(self) -> dict[str, ToolKit]:
        return self._available_kits

    @staticmethod
    def _check_unique(kits: list[ToolKit]) -> None:
        seen_kits: set[str] = set()
        seen_tools: dict[str, str] = {}
        for kit in kits:
            if kit.name in seen_kits:
                raise ToolKitError(
                    message=f"Duplicate kit name {kit.name!r}", kit_name=kit.name
                )
            seen_kits.add(kit.name)
            for tool_name in kit.tools:
                if tool_name in seen_tools:
                    raise ToolKitError(
                        message=(
                            f"Tool {tool_name!r} in kit {kit.name!r} already "
                            f"exists in kit {seen_tools[tool_name]!r}"
                        ),
                        kit_name=kit.name,
                    )
                seen_tools[tool_name] = kit.name

    def _index_tools(self, kit: ToolKit) -> None:
        for tool_name in kit.tools:
            self._tool_to_kit[tool_name] = kit.name

    def list_kits(self) -> ToolResult[dict[str, str]]:
        """List toolkits that can be enabled with register_kit.

        Returns a mapping of toolkit name to a short description.
        """
        data = {name: kit.desc for name, kit in self._available_kits.items()}
        return ToolResult(ok=True, message=f"{len(data)} kits available", data=data)

    def register_kit(self, kit_name: str) -> ToolResult[str]:
        """Enable a toolkit so its tools become available for use.

        Call this before trying to use any tool that belongs to a toolkit
        which is not yet active. Once registered, all tools inside that
        toolkit can be called directly by name.

        Args:
            kit_name: The exact name of the toolkit to register (case-sensitive).
        """
        if kit_name in self._registered_kits:
            return ToolResult(ok=False, message=f"Kit {kit_name!r} is already active")

        if kit_name not in self._available_kits:
            logger.warning("Tried to register an unknown kit: %s", kit_name)
            return ToolResult(
                ok=False,
                message=f"Unknown kit {kit_name!r}. Use list_kits to see valid names",
            )

        kit = self._available_kits.pop(kit_name)
        self._registered_kits[kit_name] = kit
        self._index_tools(kit)

        logger.info("Kit registered: %s (%d tools)", kit_name, len(kit.tools))
        return ToolResult(ok=True, message=f"Kit {kit_name!r} is now active")

    def unregister_kit(self, name: str) -> None:
        if name in self._core_kits:
            logger.warning("Refusing to unregister core kit: %s", name)
            return
        if name not in self._registered_kits:
            logger.warning("Tried to unregister an inactive kit: %s", name)
            return

        kit = self._registered_kits.pop(name)
        self._available_kits[name] = kit
        for tool_name in kit.tools:
            del self._tool_to_kit[tool_name]
        logger.info("Kit unregistered: %s", name)

    @staticmethod
    def _fail(
        agent_name: str,
        message: str,
        kit_name: str | None,
        tool_name: str | None,
    ) -> ToolExecutionError:
        """Log a failed execution and build the exception to raise."""
        logger.warning(
            "Tool failed: agent=%s kit=%s tool=%s message=%s",
            agent_name,
            kit_name,
            tool_name,
            message,
        )
        return ToolExecutionError(message, kit_name, tool_name)

    async def execute_tool(
        self, agent_name: str, tool_name: str, kwargs: dict[str, object]
    ) -> ToolResult[Any]:
        # Logged first so invalid/unknown names are recorded too.
        # Only argument names are logged, never values.
        logger.info(
            "Tool attempt: agent=%s tool=%r args=%s",
            agent_name,
            tool_name,
            sorted(kwargs),
        )

        if not re.fullmatch(TOOL_NAME_RGX, tool_name):
            raise self._fail(agent_name, f"Invalid tool name: {tool_name}", None, None)

        kit_name = self._tool_to_kit.get(tool_name)
        if kit_name is None:
            raise self._fail(agent_name, f"Unknown tool: {tool_name}", None, tool_name)

        tool = self._registered_kits[kit_name].tools[tool_name]

        missing, extra = self._check_kwargs(tool, kwargs)
        if missing:
            raise self._fail(
                agent_name, f"Missing arguments: {missing}", kit_name, tool_name
            )
        if extra:
            raise self._fail(
                agent_name, f"Unexpected arguments: {extra}", kit_name, tool_name
            )

        # run async tools directly, sync tools in a thread
        try:
            if inspect.iscoroutinefunction(tool.func):
                result = await tool.func(**kwargs)
            else:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None, functools.partial(tool.func, **kwargs)
                )
        except Exception as e:
            logger.exception(
                "Tool raised: agent=%s kit=%s tool=%s", agent_name, kit_name, tool_name
            )
            raise ToolExecutionError(
                f"Tool {tool.name!r} raised an exception: {e}",
                tool.kit_name,
                tool.name,
            ) from e

        if not isinstance(result, ToolResult):
            raise self._fail(
                agent_name,
                f"Tool {tool.name!r} returned {type(result).__name__}, expected ToolResult",
                tool.kit_name,
                tool.name,
            )

        logger.info(
            "Tool result: agent=%s kit=%s tool=%s ok=%s message=%s",
            agent_name,
            kit_name,
            tool_name,
            result.ok,
            result.message,
        )
        return result

    @staticmethod
    def _check_kwargs(
        tool: Tool, kwargs: dict[str, object]
    ) -> tuple[list[str], list[str]]:
        missing = [name for name in tool.required if name not in kwargs]
        extra = [key for key in kwargs if key not in tool.param_names]
        return missing, extra


KITS = scan_toolkit_dir()
REGISTRY = ToolkitRegistry(KITS)
