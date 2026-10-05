---
# name: the kit's name as agents see it. Short kebab-case, unique across kits.
# description: required. A missing or empty value stops the app from starting.
#   Wrap it in quotes if it contains a colon followed by a space.
# core: optional. true = always active, no register_kit step. Default false.
name: my-toolkit
description: How to use the <what it does> tools (tool_one, tool_two, tool_three) correctly and safely. Use this whenever a task involves <situations that should make the agent reach for this kit>. Consult this before calling any of these tools, not just when a call fails.
# core: false
---

# My Toolkit

<!--
This whole file (below the frontmatter) is added to the agent's system prompt
whenever the kit is enabled, on every request. Keep it short and specific:
rules and gotchas the model could not guess from the tool docstrings.
Delete these comments and every section that does not apply.
-->

One or two sentences on what these tools operate on and any hard limits
(a sandbox root, an API, a rate limit, a read-only mode).

All tools return a `ToolResult`: `ok` (bool), `message` (short status or error),
and `data` (the payload, or `None`). **Check `ok` first, then read `data` for
the payload. Don't parse results out of `message`.** `message` is for
explaining outcomes to the user.

## Picking the right tool

- `tool_one`: when to use it, and what it returns in `data`.
- `tool_two`: when to use it instead of `tool_one`.
- `tool_three`: the lightweight check to run before the others.

If it isn't obvious which tool applies, say how to decide (for example, check
the file extension first) so the model doesn't guess by trial and error.

## Before you change anything

Describe any tool that overwrites, replaces, or sends something:

- What is lost or sent, and whether it can be undone.
- What the agent should check first (read it, list it, look it up).
- When to ask the user instead of acting.

## Destructive actions need confirmation

If a tool uses the `confirm` pattern, spell out the exact sequence:

1. Call `dangerous_tool(target)` with no `confirm`. It only reports what it would do.
2. Show the user exactly what will be affected and ask for an explicit yes.
3. Only then call `dangerous_tool(target, confirm=True)`, or `confirm=False` if they decline.

Never infer `confirm=True` from a general instruction like "clean everything
up". Get an explicit yes for the specific target.

## Error handling

- When a call returns `ok=False`, tell the user what `message` says. Don't
  retry the same call over and over, because most failures won't fix themselves.
- Name anything that is blocked on purpose (a denied path, a protected
  resource) and say it is a hard rule, not something to work around.

## Common workflows

- "Do X" → `tool_one`, then `tool_two`.
- "Check Y first" → `tool_three`, then decide.
- "Undo Z" → what to call, and what is not recoverable.
