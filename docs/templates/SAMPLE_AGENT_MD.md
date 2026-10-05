---
name: Agent                  # unique across all agents; this is the name shown in the UI
type: complete                # "complete" (chat agent) or "basic" (one-shot helper)
language_model: deepseek/deepseek-v4-flash   # any valid OpenRouter model ID

# complete agents only (a basic agent with either of these is rejected)
image_path: avatar.png        # optional avatar filename
max_loop: 40                  # max tool-calling loops per run; default 40

# every param is optional; omit one (or leave it commented out) to use its default
params:
  temperature: 1.0            # float, default 1.0
  top_p: 1.0                  # float, default 1.0
  frequency_penalty: 0.0      # float, default 0.0
  presence_penalty: 0.0       # float, default 0.0
  reasoning_effort: medium    # low | medium | high (omit for none)
  # max_completion_tokens: 4096   # int (omit for no limit)
  # seed: 42                      # int (omit for random)
  # stop: ["###"]                 # list of strings
  # response_format:              # dict, e.g. JSON mode
  #   type: json_object
---

Write the agent's persona and system prompt here, in plain Markdown.
Everything below the closing `---` becomes the system prompt.
