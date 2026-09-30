import importlib
import inspect
import logging
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import get_origin

import frontmatter

from modules.errors import ProgramError
from modules.toolkits.builder import build_toolkit
from modules.toolkits.errors import ToolKitError
from modules.toolkits.models import ToolBlueprint, ToolKit, ToolResult

logger = logging.getLogger(__name__)

kits_path = Path(__file__).resolve().parent / "kits"


def _collect_tool_funcs(tools_module: ModuleType) -> list[Callable[..., object]]:
    funcs: list[Callable[..., object]] = []

    for name, func in inspect.getmembers(tools_module, inspect.isfunction):
        if func.__module__ != tools_module.__name__:
            continue

        if not getattr(func, "_tool_tag", False):
            logger.debug("Ignoring %s: not decorated with @register_tool", name)
            continue

        return_type = inspect.signature(func).return_annotation
        if return_type is inspect.Signature.empty:
            logger.warning("Ignoring %s: missing return type annotation", name)
            continue

        if (get_origin(return_type) or return_type) is not ToolResult:
            logger.warning("Ignoring %s: does not return ToolResult", name)
            continue

        funcs.append(func)

    return funcs


def scan_toolkit_dir() -> list[ToolKit]:
    if not kits_path.exists():
        raise ProgramError(f"{kits_path} could not be found. Unable to build toolkits")

    kits: list[ToolKit] = []

    for item in sorted(kits_path.iterdir()):
        if not item.is_dir() or item.name.startswith(("__", ".")):
            continue

        package = f"modules.toolkits.kits.{item.name}"
        skill_file = item / "SKILL.md"

        if not (item / "tools.py").exists():
            raise ToolKitError(
                message=f"{package} is missing a tools.py", kit_name=item.name
            )
        if not skill_file.exists():
            raise ToolKitError(
                message=f"{package} is missing a SKILL.md", kit_name=item.name
            )

        try:
            tools_module = importlib.import_module(f"{package}.tools")
        except ImportError as e:
            raise ToolKitError(
                message=f"Failed to load {package}: {e}", kit_name=item.name
            ) from e

        post = frontmatter.load(skill_file)
        metadata = post.metadata
        kit_name = str(metadata.get("name", "")).strip()
        desc = str(metadata.get("description", "")).strip()
        if not desc:
            raise ToolKitError(
                message=f"{item.name}/SKILL.md needs a 'description' in its frontmatter",
                kit_name=item.name,
            )
        core = bool(metadata.get("core", False))

        funcs = _collect_tool_funcs(tools_module)
        if not funcs:
            logger.warning("Kit %s has no valid tools, skipping", item.name)
            continue

        blueprints = [
            ToolBlueprint(func=f, params_to_ignore=getattr(f, "_ignore_params", []))
            for f in funcs
        ]

        try:
            kit = build_toolkit(kit_name, desc, post.content, blueprints, core)
        except Exception as e:
            raise ToolKitError(
                message=f"Failed to build schemas for kit {item.name}: {e}",
                kit_name=item.name,
            ) from e

        kits.append(kit)
        logger.debug("Built kit %s with %d tools", item.name, len(blueprints))

    return kits
