# Creating a Toolkit

A toolkit is a folder with two files: `tools.py`, which holds the functions an agent can call, and `SKILL.md`, which tells the agent how to use them well. KAgent scans the kits folder at startup, so there is nothing to register by hand.

---

## Quick start

1. **Create a folder** `src/modules/toolkits/kits/<kit_name>/`, for example `kits/weather/`.
2. **Copy the templates** into it:
   - `sample_tools.py` becomes `tools.py`
   - `SAMPLE_SKILL_MD.md` becomes `SKILL.md`
3. **Write your tools** in `tools.py`. Delete the examples you don't need.
4. **Write the skill instructions** in `SKILL.md`. Set `name` and `description` in its frontmatter.
5. **Restart KAgent.** Kits are scanned once at startup.
6. **Try it.** Ask an agent to list its kits, enable yours, and use a tool from it.

```text
toolkits/kits/
├── file/
│   ├── SKILL.md
│   └── tools.py
└── weather/            <- your new kit
    ├── SKILL.md
    └── tools.py
```

---

## How agents find and use a kit

Core tools (including `list_kits` and `register_kit`) are always active. Everything else starts as an available kit:

1. The agent calls `list_kits` to see what exists.
2. It calls `register_kit` to enable the one it needs.
3. From then on its tools are offered to the model, and the kit's `SKILL.md` is added to the system prompt.

So the `description` in `SKILL.md` is what helps an agent decide whether to enable the kit, and the body is what guides it once the kit is on.

---

## Writing `tools.py`

Every tool is a plain function with the `@register_tool()` decorator (parentheses included).

```python
from modules.toolkits.decorators import register_tool
from modules.toolkits.models import ToolResult


@register_tool()
def get_forecast(city: str, days: int = 3) -> ToolResult[list[str]]:
    """Returns the weather forecast for `city` for the next `days` days.

    Use this when the user asks about future weather. Fails if the city
    is not found.
    """
    ...
    return ToolResult(ok=True, message="Forecast retrieved", data=lines)
```

### Rules

| Rule | Why |
| --- | --- |
| **Annotate every parameter and the return type.** | The annotations describe the tool to the model. Stick to simple types such as `str`, `int`, `float`, `bool`, and `list[str]`. |
| **Write a docstring.** | The model reads it as the tool's description. Give a one-line summary, then say when to use it and when not to. |
| **Return a `ToolResult`.** | This is the only shape the agent loop understands. |
| **Don't raise for expected failures.** | Return `ok=False` with a clear `message` so the model can read it and try again. |
| **Give optional inputs defaults.** | `limit: int = 10` makes the argument optional. |
| **Prefix helpers with `_`.** | Underscore functions are not tools. |
| **Keep tool names unique across all kits.** | The registry looks tools up by name, so two kits with the same tool name can collide. |

### `ToolResult`

| Field | Meaning |
| --- | --- |
| `ok` | `True` if the tool did what was asked. `False` for any failure, including "needs confirmation". |
| `message` | A short human-readable status or error. The model reads it, and the UI shows a preview of it. |
| `data` | The payload (text, a list, a dict), or `None`. Put results here, never only in `message`. |
| `expose_data` | Controls whether `data` is included in what the model sees. The existing file tools rely on the default. |

`ToolResult` is generic, so annotate it as `ToolResult[str]`, `ToolResult[list[str]]`, `ToolResult[dict[str, object]]`, and so on.

### Sync vs. async

Both work. `async def` tools are awaited. Plain `def` tools are run in a worker thread, so a slow blocking call won't freeze the app. Use `async def` when the library you call is async, as most HTTP clients are.

### Safety patterns

- **Validate inputs first.** If a tool touches the filesystem, run every path through a check like `validate_path` in the file kit, which resolves the path and refuses anything outside the working directory or hidden.
- **Destructive tools use the confirm pattern.** `confirm: bool | None = None`:
  - `None`: only report what would happen, return `ok=False`.
  - `False`: the user declined, return `ok=False`.
  - `True`: do the work.

  `dangerous_tool` in the template shows the full shape.
- **Overwrite-style flags default to off.** For example, `overwrite: bool = False`, and say in the docstring that the agent must confirm with the user first.
- **Catch specific exceptions** (`FileNotFoundError`, `PermissionError`, and so on) and return a message that says what went wrong.

---

## Writing `SKILL.md`

```markdown
---
name: weather-tools
description: How to use the weather tools (get_forecast, ...) ... Use this whenever ...
---

# Weather Tools

Instructions for the model, in Markdown.
```

### Frontmatter

| Field | Description |
| --- | --- |
| `name` | Short kebab-case identifier for the kit. |
| `description` | What the kit does, the tools in it, and **when to use it**. Include the situations and keywords that should make an agent enable it. End with "Consult this before calling any of these tools". |

> [!WARNING]
> The `description` is YAML. If it contains a colon followed by a space, or starts with a special character, wrap the whole value in quotes, otherwise the file fails to parse.

### Body

The body is added to the system prompt on every request while the kit is enabled, so every line costs tokens. Keep it to what the model can't work out from the docstrings:

- Which tool to pick when several look similar.
- What to check before an overwrite, send, or delete.
- The exact confirmation sequence for destructive tools.
- Hard limits (sandbox, blocked files, rate limits) that are on purpose and shouldn't be worked around.
- Short multi-step workflows ("to edit a file, read it, then write the full new contents").

Don't repeat the docstrings or list every parameter. The filesystem kit's `SKILL.md` is a good model to follow.

---

## Testing a new kit

1. Restart the app and check `logs/app.log`. A kit with a broken `tools.py` or `SKILL.md` should be reported there.
2. Ask an agent: "list your toolkits". Your kit should appear.
3. Ask it to enable the kit, then give it a task that needs your tools. Watch the status line for "Running tool_name...".
4. Test the failure paths too: bad input, missing target, and declining a confirmation.

The `tests/` folder is empty, but pure functions in `tools.py` are easy to unit-test with `pytest` once you add tests, because they only take plain arguments and return a `ToolResult`.

---

## Troubleshooting

| Problem | Likely cause |
| --- | --- |
| The kit isn't listed | The folder isn't under `toolkits/kits/`, a file is misnamed (it must be exactly `tools.py` and `SKILL.md`), or the app wasn't restarted. |
| The kit is listed but a tool is missing | The function lacks `@register_tool()`, is named with a leading underscore, or an import error stopped `tools.py` from loading. Check the log. |
| The model never uses the kit | The `description` doesn't say when to use it. Add the situations and keywords. |
| The model misuses a tool | The docstring is vague, or `SKILL.md` is missing the rule. Add it in one short line. |
| `SKILL.md` fails to parse | Unquoted colon in the `description`, or missing `---` fences. |
| Tool arguments come through wrong | Missing or unusual type annotations. Use simple types. |
| A tool "succeeds" but the model sees nothing | The result was only in `message`. Put the payload in `data`. |
