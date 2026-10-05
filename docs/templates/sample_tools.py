"""Tools for the my-toolkit toolkit.

Copy this file to src/modules/toolkits/kits/<kit_name>/tools.py, next to the
kit's SKILL.md, then replace the examples below with your own tools.

The folder name must be a valid Python identifier (snake_case, no hyphens),
because it is imported as modules.toolkits.kits.<folder>.

Rules every tool follows (the scanner skips a tool that breaks the first three):
  - Decorate it with @register_tool() (note the parentheses). Functions
    without the decorator are ignored, which is what makes them safe helpers.
  - Annotate the return type as ToolResult or ToolResult[...]. A missing
    annotation or any other return type gets the tool skipped, with only a
    warning in logs/app.log.
  - Define it in this file. Functions imported from other modules are ignored.
  - Annotate every parameter with plain types (str, int, float, bool,
    list[str]). The annotations become the schema the model sees, and an
    unsupported one fails the kit's build at startup.
  - Write a docstring. The first line is a one-sentence summary, and the rest
    explains when to use it and when not to. The model reads this text.
  - Don't let expected failures raise: return ok=False with a message the
    model can act on.

Do NOT add `from __future__ import annotations` to this file. It turns the
annotations into strings, so every tool would be skipped.
"""

from modules.toolkits.decorators import register_tool
from modules.toolkits.models import ToolResult

# ---------- helpers (not exposed to the model) ----------


def _is_blocked(name: str) -> bool:
    """Example guard. Put validation shared by several tools in helpers like this."""
    return name.strip() == "" or name.startswith(".")


# ---------- read-only tool ----------


@register_tool()
def tool_one(name: str) -> ToolResult[str]:
    """Looks up the thing called `name` and returns its text.

    Use this to inspect something before changing it. Fails if `name` is
    empty, blocked, or does not exist.
    """
    if _is_blocked(name):
        return ToolResult(ok=False, message=f"Access denied: '{name}' is not allowed.")
    try:
        result = f"Details for {name}"  # replace with real work
    except PermissionError:
        return ToolResult(ok=False, message=f"Permission denied for '{name}'")
    return ToolResult(ok=True, message="Looked up successfully", data=result)


# ---------- tool with an optional argument and a list result ----------


@register_tool()
def tool_two(query: str, limit: int = 10) -> ToolResult[list[str]]:
    """Searches for entries matching `query` and returns up to `limit` of them.

    Returns an empty list (still ok=True) when nothing matches, so check
    `data` instead of assuming a failure.
    """
    if limit < 1:
        return ToolResult(ok=False, message="limit must be at least 1")
    matches = [f"{query} #{i}" for i in range(1, 4)]  # replace with real work
    message = "No matches" if not matches else "Search completed"
    return ToolResult(ok=True, message=message, data=matches[:limit])


# ---------- cheap existence check ----------


@register_tool()
def tool_three(name: str) -> ToolResult[dict[str, object]]:
    """Returns whether `name` exists and basic metadata about it.

    Use this as the lightweight first step before reading, changing, or
    deleting something.
    """
    if _is_blocked(name):
        return ToolResult(ok=False, message=f"Access denied: '{name}' is not allowed.")
    info: dict[str, object] = {"exists": True, "kind": "example"}  # replace
    return ToolResult(ok=True, message="Info retrieved", data=info)


# ---------- async tool (for network calls and other awaitable work) ----------


@register_tool()
async def tool_async(url: str) -> ToolResult[str]:
    """Fetches `url` and returns the response text.

    Async tools are awaited. Plain `def` tools run in a worker thread, so
    both styles work. Prefer `async def` when the library you call is async.
    """
    # import httpx
    # async with httpx.AsyncClient(timeout=10) as client:
    #     response = await client.get(url)
    #     response.raise_for_status()
    #     return ToolResult(ok=True, message="Fetched", data=response.text)
    return ToolResult(ok=False, message="Not implemented")


# ---------- destructive tool with the two-step confirm pattern ----------


# WARNING: this deletes something. It never acts without confirm=True.
@register_tool()
def dangerous_tool(target: str, confirm: bool | None = None) -> ToolResult[str]:
    """Deletes `target`. This is destructive and requires explicit user confirmation.

    Call this first with `confirm` unset to see what would be deleted. Only
    pass confirm=True after the user has explicitly agreed, or confirm=False
    if they decline.
    """
    if _is_blocked(target):
        return ToolResult(
            ok=False, message=f"Access denied: '{target}' is not allowed."
        )

    # Step 1: a bare call only reports, it never acts.
    if confirm is None:
        return ToolResult(
            ok=False,
            message=f"'{target}' would be deleted. Ask the user to confirm, then call again with confirm=True.",
        )
    # Step 2: the user said no.
    if not confirm:
        return ToolResult(ok=False, message="The user denied the request")

    # Step 3: confirmed, so do the work.
    try:
        pass  # replace with the real deletion
    except OSError as e:
        return ToolResult(ok=False, message=f"Failed to delete '{target}': {e}")
    return ToolResult(ok=True, message=f"'{target}' was deleted")
