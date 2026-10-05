# Creating an Agent

An agent in KAgent is a single Markdown file. The YAML frontmatter at the top holds its settings, and everything below the frontmatter is its persona prompt. There is no code to write.

---

## Quick start

1. **Copy the template.** Duplicate `docs/templates/SAMPLE_AGENT_MD.md`.
2. **Move it** into `src/modules/agents/definitions/` and rename it (for example `LUNA.md`). Only `.md` files are loaded.
3. **Edit the frontmatter:** set a unique `name`, pick `type` and `language_model`, and adjust the params.
4. **Write the persona** below the closing `---`.
5. **(Optional) Add an avatar** image to `src/modules/agents/avatars/` and set `image_path` to its filename.
6. **Restart KAgent.** Agents are built once at startup, so edits are not picked up while the app is running.

The new agent appears in the left panel. If it doesn't, check the log (see [Troubleshooting](#troubleshooting)).

---

## File layout

```markdown
---
name: Luna
type: complete
language_model: deepseek/deepseek-v4-flash
image_path: luna.png
max_loop: 40
params:
  temperature: 0.8
  reasoning_effort: medium
---

The persona prompt goes here, in plain Markdown.
```

---

## Frontmatter reference

| Field | Required | Applies to | Description |
| --- | :-: | --- | --- |
| `name` | Yes | both | Display name. Must be **unique** across all agents (see [Troubleshooting](#troubleshooting)). |
| `type` | Yes | both | `complete` for a chat agent with history, tools, and memory. `basic` for a stateless one-shot helper. |
| `language_model` | Yes | both | Any valid OpenRouter model ID, for example `deepseek/deepseek-v4-flash`. |
| `image_path` | No | complete only | Avatar filename. A `basic` agent must not have this key at all. |
| `max_loop` | No | complete only | Maximum tool-calling loops per run. Defaults to 40. A `basic` agent must not have this key at all. |
| `params` | No | both | Model parameters, listed below. Every one is optional. |

> [!WARNING]
> Unknown keys are rejected. A typo such as `temprature` makes the whole agent get skipped, with a warning only in the log.

### `params`

| Param | Type | Description |
| --- | --- | --- |
| `temperature` | float | Randomness. Lower is more focused, higher is more creative. |
| `top_p` | float | Nucleus sampling cutoff. |
| `frequency_penalty` | float | Discourages repeating the same tokens. |
| `presence_penalty` | float | Encourages new topics. |
| `reasoning_effort` | `low` / `medium` / `high` | How much the model reasons. Omit for none. |
| `max_completion_tokens` | int | Upper limit on reply length. Omit for no limit. |
| `seed` | int | Fixed seed for more repeatable output. Omit for random. |
| `stop` | list of strings | Sequences that end generation. |
| `response_format` | dict | For example `{type: json_object}` for JSON mode. |

Leave out any param you don't need and the default is used.

---

## Complete vs. basic agents

| | Complete | Basic |
| --- | --- | --- |
| Shown in the UI | Yes | No |
| Keeps message history | Yes | No, every call is a fresh system + user exchange |
| Can use tools | Yes | No |
| Uses memory recall | Yes | No |
| Gets `GLOBAL_SYSTEM_PROMPT.md` | Yes | No, only its own prompt |
| `image_path` / `max_loop` | Allowed | Must be omitted |

Use **complete** for anything a person chats with. Use **basic** for background helpers such as summarizers.

> [!NOTE]
> Memory creation depends on one basic agent named exactly `MEMORY_EXTRACTOR`. If you rename or delete it, memories are still recalled but no new ones are created.

---

## Writing the persona prompt

For a **complete** agent, the system prompt is built from three parts, in this order:

1. The shared `GLOBAL_SYSTEM_PROMPT.md`, which applies to every complete agent.
2. Your persona text (everything below the frontmatter).
3. The instructions of the enabled toolkits, added automatically.

So the persona only needs to cover what makes this agent different. Don't repeat the rules from the global prompt.

Tips:

- **Be specific about voice.** Describe tone, vocabulary, and how formal or playful the agent is, and give a short example line or two.
- **Say what it should and shouldn't do.** Short rules work better than long paragraphs.
- **Keep it focused.** The persona is sent on every request, so a very long prompt adds cost to every message.
- **Don't put secrets in it.** The prompt is plain text on disk, and models can be coaxed into repeating it.

---

## Examples

### A chat agent

```markdown
---
name: Luna
type: complete
language_model: deepseek/deepseek-v4-flash
image_path: luna.png
max_loop: 50
params:
  temperature: 0.8
  reasoning_effort: low
---

You are Luna, a calm and curious study companion.

- Explain things step by step, using short everyday examples.
- Ask one clarifying question when a request is vague, then proceed.
- Keep a warm, relaxed tone and avoid jargon unless the user uses it first.
```

### A background helper

```markdown
---
name: TITLE_WRITER
type: basic
language_model: deepseek/deepseek-v4-flash
params:
  temperature: 0.3
---

Write a title of at most six words for the conversation you are given.
Reply with the title only.
```

Note that the basic agent has no `image_path` and no `max_loop`.

---

## Troubleshooting

| Problem | Likely cause |
| --- | --- |
| The agent doesn't appear | The file isn't a `.md` file, isn't in `definitions/`, has invalid YAML, or has an unknown or misspelled key. Check the log for a warning that names the file. |
| The agent doesn't appear, and it is `basic` | That is expected. Basic agents are hidden from the chat list. |
| Two agents show up but behave the same | They share a `name`. The later file overwrites the earlier one, but both still appear in the list. Give each agent a unique name. |
| A `basic` agent is rejected | It contains `image_path` or `max_loop`. Remove the keys entirely. |
| Changes have no effect | Restart the app. Only the QML interface hot-reloads. |
| Replies are cut off or loop forever | Raise or lower `max_loop`, or set `max_completion_tokens`. Note that `max_loop: 0` falls back to 40 and negative values aren't rejected. |
| The model errors on every request | The `language_model` ID is not a valid OpenRouter model, or the model doesn't support reasoning (a reasoning request is always sent). |

The log file is `logs/app.log`.

---
