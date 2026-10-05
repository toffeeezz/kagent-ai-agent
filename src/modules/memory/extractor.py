import json
import logging
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from modules.database.models import MessageRow
from modules.memory.service import remember
from modules.server.server import Server

if TYPE_CHECKING:
    from modules.agents.models import BasicAgent

logger = logging.getLogger(__name__)

MAX_ITEMS = 5


def _parse(raw: str) -> list[dict[str, object]]:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: grab the outermost {...} or [...] if the model added prose.
        match = re.search(r"\{.*\}|\[.*\]", raw, re.DOTALL)
        if match is None:
            return []
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return []

    if isinstance(data, dict):
        data = data.get("memories", [])
    if not isinstance(data, list):
        return []
    return [
        d for d in data if isinstance(d, dict) and isinstance(d.get("content"), str)
    ]


async def extract_and_store(
    server: Server,
    extractor: "BasicAgent",
    agent_name: str,
    rows: Sequence[MessageRow],
) -> None:
    """Never raises: a failed extraction must not affect the chat."""
    try:
        transcript = "\n".join(f"{r.speaker_name}: {r.text}" for r in rows)
        response = await extractor.generate(server, "extractor", transcript)
        items = _parse(response.content or "")[:MAX_ITEMS]
        ids = [r.id for r in rows]
        for item in items:
            try:
                importance = min(1.0, max(0.0, float(item.get("importance", 0.5))))  # pyright: ignore[reportArgumentType]
            except (TypeError, ValueError):
                importance = 0.5
            _ = await remember(
                server, agent_name, str(item["content"]), importance, ids
            )
        logger.info("Extracted %d memories: agent=%s", len(items), agent_name)
    except Exception:
        logger.exception("Memory extraction failed: agent=%s", agent_name)
