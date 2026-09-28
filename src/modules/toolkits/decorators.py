from collections.abc import Callable


def register_tool(params_to_ignore: list[str] | None = None):
    """Mark a function as a tool so the scanner picks it up."""

    def decorator(func: Callable[..., object]):
        func.__dict__["_ignore_params"] = params_to_ignore or []
        func.__dict__["_tool_tag"] = True
        return func

    return decorator
