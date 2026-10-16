import logging
import re
import shutil
from pathlib import Path
from typing import Any

import frontmatter
import yaml
from pydantic import ValidationError

from modules.agents.builder import AGENT_AVATAR_DIR, AGENT_DEFINITION_DIR
from modules.agents.errors import AgentError
from modules.agents.models import AgentDefinition

logger = logging.getLogger(__name__)

AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_SAFE_NAME_RGX = re.compile(r"[^A-Za-z0-9_ -]+")


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME_RGX.sub("_", name.strip())
    return cleaned.strip(" _-") or "agent"


def _import_avatar(source: str, name: str) -> str:
    source_path = Path(source)
    if not source_path.is_file():
        raise AgentError(f"Avatar image not found: {source_path}", name)

    ext = source_path.suffix.lower()
    if ext not in AVATAR_EXTENSIONS:
        raise AgentError(
            f"Unsupported avatar format '{ext}'. Use png, jpg, jpeg, webp or gif.",
            name,
        )

    AGENT_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_filename(name)}{ext}"
    _ = shutil.copy2(source_path, AGENT_AVATAR_DIR / filename)
    logger.info("Imported avatar %s -> %s", source_path, filename)
    return filename


def create_agent_file(
    *,
    name: str,
    agent_type: str,
    language_model: str,
    persona: str,
    avatar_source: str = "",
    max_loop: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    reasoning_effort: str | None = None,
    max_completion_tokens: int | None = None,
    seed: int | None = None,
    stop: list[str] | None = None,
    response_format: dict[str, object] | None = None,
) -> AgentDefinition:
    name = name.strip()
    agent_type = agent_type.strip().lower()
    language_model = language_model.strip()

    if not name:
        raise AgentError("Agent name cannot be empty", name or "agent")
    if agent_type not in ("basic", "complete"):
        raise AgentError(
            f"Invalid agent type {agent_type!r}: expected 'basic' or 'complete'",
            name,
        )
    if not language_model:
        raise AgentError("Language model cannot be empty", name)
    if not persona.strip():
        raise AgentError("Persona prompt cannot be empty", name)

    params: dict[str, Any] = {}
    if temperature is not None:
        params["temperature"] = temperature
    if top_p is not None:
        params["top_p"] = top_p
    if frequency_penalty is not None:
        params["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        params["presence_penalty"] = presence_penalty
    if reasoning_effort:
        params["reasoning_effort"] = reasoning_effort
    if max_completion_tokens is not None:
        params["max_completion_tokens"] = max_completion_tokens
    if seed is not None:
        params["seed"] = seed
    if stop is not None and stop:
        params["stop"] = stop
    if response_format is not None:
        params["response_format"] = response_format

    data: dict[str, Any] = {
        "name": name,
        "type": agent_type,
        "language_model": language_model,
    }
    if agent_type == "complete":
        if avatar_source:
            data["image_path"] = _import_avatar(avatar_source, name)
        if max_loop is not None:
            data["max_loop"] = max_loop
    if params:
        data["params"] = params

    try:
        definition = AgentDefinition.model_validate(data)
    except ValidationError as e:
        raise AgentError(f"Invalid agent definition: {e}", name) from e

    path = AGENT_DEFINITION_DIR / f"{_safe_filename(name)}.md"
    if path.exists():
        raise AgentError(
            f"An agent definition already exists at {path.name}. "
            "Agent names must be unique.",
            name,
        )

    frontmatter_yaml = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    path.write_text(
        f"---\n{frontmatter_yaml}---\n\n{persona.strip()}\n", encoding="utf-8"
    )
    logger.info(
        "Created agent definition: name=%s type=%s model=%s file=%s",
        name,
        agent_type,
        language_model,
        path.name,
    )
    return definition


def delete_agent_file(name: str) -> None:
    name = name.strip()
    if not name:
        raise AgentError("Agent name cannot be empty", name)

    target: Path | None = None
    image_path: str | None = None
    for file in AGENT_DEFINITION_DIR.iterdir():
        if not file.is_file() or file.suffix != ".md":
            continue
        try:
            post = frontmatter.load(file)
        except Exception:
            continue
        if post.metadata.get("name") == name:
            target = file
            image_path = post.metadata.get("image_path")
            break

    if target is None:
        raise AgentError(f"Agent '{name}' could not be found", name)

    target.unlink()
    if image_path:
        avatar = AGENT_AVATAR_DIR / image_path
        if avatar.is_file():
            avatar.unlink()
    logger.info("Deleted agent definition: name=%s file=%s", name, target.name)