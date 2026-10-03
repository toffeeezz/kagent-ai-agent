---
name: git_operations
description: >-
  Provides basic git version control operations including checking repository
  status, staging files, committing changes, viewing diffs, and restoring
  files. Wraps the `git` CLI directly and returns raw command output.
  Triggers: "git status", "stage this file", "commit these changes", "show me the diff",
  "what changed", "is this staged", "add to git", "check repo status",
  "discard changes", "unstage this file", "revert this file", "restore this file".
  Do NOT use for generic file reading/writing/deletion, remote operations
  (push, pull, clone, fetch), branch management, merge/rebase, or any git
  command not explicitly listed below.
---
## Description
A collection of utility functions for interacting with a local git repository via subprocess calls to the `git` CLI. Each tool operates on a specified working directory and returns the raw stdout/stderr from the underlying git command, unmodified, so it should be read directly rather than re-interpreted.
---
## Tool API Reference
### 1. `git_status`
Runs `git status` in the given directory and returns the result.
* **Parameters:**
  * `path` (`str`): The filesystem path of the git repository to check.
* **Returns:** `tuple[bool, str]` — `(True, output)` on success, where output is the raw stdout of `git status` (branch info, staged/unstaged changes, untracked files) exactly as it would appear in a terminal. `(False, error_message)` on failure.
* **Note:** Present the full status report to the user in a table.
---
### 2. `git_add`
Stages a file with `git add` inside a given repository.
* **Parameters:**
  * `cwd_path` (`str`): The working directory of the git repository.
  * `file_path` (`str`): The path of the file to stage, relative to `cwd_path`.
* **Returns:** `tuple[bool, str]` — `(True, output)` on success, where output is stdout from `git add` (almost always empty — no output means it worked). `(False, error_message)` on failure.
---
### 3. `git_commit`
Creates a commit with the given message using `git commit`.
* **Parameters:**
  * `cwd_path` (`str`): The working directory of the git repository.
  * `commit_msg` (`str`): The commit message to use.
* **Returns:** `tuple[bool, str]` — `(True, output)` on success, where output confirms what was committed (e.g. `[main <hash>] <message>` plus a file-change summary) — read it to confirm the commit actually landed. `(False, error_message)` on failure.
---
### 4. `git_diff`
Shows the diff of a file using `git diff`.
* **Parameters:**
  * `cwd_path` (`str`): The working directory of the git repository.
  * `file_path` (`str`): The path of the file to diff, relative to `cwd_path`.
* **Returns:** `tuple[bool, str]` — `(True, output)` on success, where output is the unified diff (`+`/`-` prefixed lines). An empty string means no diff (file unchanged, or already staged). `(False, error_message)` on failure.
---
### 5. `git_restore`
Restores a file's contents using `git restore`, discarding local changes according to the flags passed in.
* **Parameters:**
  * `cwd_path` (`str`): The working directory of the git repository.
  * `file_path` (`str`): The path of the file to restore, relative to `cwd_path`.
  * `args` (`list[str]`): Additional flags inserted before `file_path` on the command line. Common values:
    * `--staged` / `-S`: restore the index (unstage) instead of the working tree.
    * `--worktree` / `-W`: restore the working tree (default target if neither this nor `--staged` is given).
    * `--source=<commit>` / `-s <commit>`: restore from a specific commit instead of the default source.
    * `--ours` / `--theirs`: restore from a specific side of an unresolved merge conflict.
    * Pass an empty list for default behavior (restore working tree from the index).
* **Returns:** `tuple[bool, str]` — `(True, output)` on success, where output is stdout from `git restore` (typically empty — no output means it worked). `(False, error_message)` on failure.
* **Warning — destructive:** This is the one tool in this module that discards data rather than just reading it or moving it into the staging area. Restoring the working tree throws away uncommitted edits to that file with no undo via these tools. **Always run `git_diff` on the file first and show the user what will be lost before calling `git_restore` on the working tree.** This confirmation step is not needed for `--staged`-only restores, since that just unstages a file without touching its working-tree contents.
* **Do not pass `-p`/`--patch`:** interactive hunk selection requires a live terminal and will hang or fail when run through a non-interactive subprocess call. If the user wants to restore only part of a file, read the diff yourself, tell them which hunks would be discarded, and let them confirm restoring the whole file, or handle it manually.
---
## Usage Guidelines & Safeguards
* **Failure modes:** All tools share the same three failure cases — `git` not found on PATH, a non-zero exit code from git (message includes git's own stderr), or a command timeout. Read the returned error message directly; it already tells you which of these occurred.
* **Order of operations:** Check `git_status` before staging, committing, or restoring, so you know what's actually changed and where. Use `git_diff` on a specific file before staging or restoring it if you want to confirm exactly what will be committed or lost.
* **Committing:** Only call `git_commit` once the relevant files have been staged with `git_add` — this module does not stage automatically, and does not support `git commit -a`.
* **Restoring:** Never call `git_restore` on a file without working-tree changes without first checking `git_diff` and getting the user's confirmation, unless the call is strictly `--staged` (unstaging only). If the user says something ambiguous like "undo my changes to X", confirm whether they mean unstage (`--staged`) or fully discard (working tree) before acting, since these have very different consequences.
* **One file, one add+commit cycle:** When the user asks you to commit multiple files, do NOT stage everything at once and write a single combined commit message. Handle each file individually in sequence — `git_diff` that one file if you are creating your own commit message, then `git_add` and `git_commit` it with a message specific to that file's actual change, before moving to the next file. Each file should end up as its own separate commit with its own tailored message, not lumped together, since a shared generic message loses the specificity of what each individual file's change actually was.
* **Commit message format:** When you need to write the message yourself (the user didn't provide one), use `git_diff` to inspect what actually changed, then format it as `<verb> <target>: <short description>`:
  * `<verb>` — a short past-tense or descriptive action word: `refactored`, `fixed`, `added`, `removed`, `renamed`, `updated`, `deleted`.
  * `<target>` — the file, module, class, or feature the change is centered on (e.g. `gui`, `handler.py`, `ChatPanel`, `memory session loading`).
  * `<short description>` — a brief, concrete summary of what changed, in plain language, not a restatement of the diff syntax.
  * Examples: `refactored gui: split chat bubble sizing into a separate helper`, `deleted handler.py: removed unused legacy request handler`, `fixed memory_manager: corrected off-by-one in session loading`, `added git_operations: new skill for status/add/commit/diff`.
  * Keep it to one line under ~72 characters where possible; only add more detail below a blank line if the change genuinely needs it (e.g. touches multiple unrelated things — though ideally that should be split into separate commits instead).
* **Scope limits:** These tools only cover status, add, commit, diff, and restore. Do not attempt to construct other git subcommands (push, pull, branch, merge, log, reset, checkout, etc.) through these functions — they are not general-purpose git wrappers.
