---
name: filesystem-tools
description: How to use the sandboxed filesystem tools (read_file, read_document, write_file, append_file, make_dir, list_dir, move_file, copy_file, get_file_info, delete_file_or_dir) correctly and safely. Use this whenever a task involves reading, writing, editing, moving, copying, organizing, or deleting files or directories on disk, including PDFs and Word docs, checking whether something exists first, or cleaning up a workspace. Consult this before calling any of these tools, not just when a call fails.
---

# Filesystem Tools

These tools operate inside a sandboxed root directory (the current working
directory at process start). Every path — absolute or relative — is resolved
and checked against that root before any I/O happens. There is no way to
escape it, so don't waste turns trying alternate path tricks (`..`, symlink-
looking paths, absolute paths outside the root) if one call is denied —
the denial is intentional, not a bug to work around.

All tools return a `ToolResult`: `ok` (bool), `message` (short human-readable
status or error), and `data` (the actual payload, or `None`). **Check `ok`
first, then read `data` for the payload — don't parse the file contents or
listing out of `message`.** `message` is for explaining outcomes to the user,
not for extracting information.

## Picking the right read tool

- `read_file` — plain text only (code, markdown, config, csv, etc.). It will
  refuse binary/non-UTF-8 files and hidden/`.env` files outright.
- `read_document` — PDF and DOCX only. Returns markdown-formatted text via
  `data`, not raw bytes. Do not try `read_file` on a `.pdf`/`.docx` — it will
  fail; go straight to `read_document` when the extension is one of those.

If you don't know a file's type ahead of time, check the extension yourself
(or `list_dir` the parent) rather than guessing by trial and error across
both tools.

## Before you overwrite or append

`write_file` **silently and permanently replaces** the entire contents of an
existing file — there's no confirmation step built in, unlike delete. Treat
any `write_file` call on a path that might already exist as something to be
deliberate about:

- If you're not sure whether the file already has content the user cares
  about, `read_file`/`read_document` it first (or `list_dir` the parent to
  check it exists) before deciding whether to overwrite or use `append_file`.
- Use `append_file` when the goal is "add to" rather than "replace" — but
  remember it requires the file to already exist; if it might not, create it
  with `write_file` first (or check with `list_dir`/`read_file`).
- When a user's request is ambiguous about overwrite vs. append ("save this
  to notes.txt" when notes.txt exists), prefer asking or appending over
  silently destroying existing content, unless context makes overwrite the
  obvious intent (e.g. "regenerate the file" or "replace the contents with").

## Deletion is a two-step, user-confirmed flow — don't shortcut it

`delete_file_or_dir` is intentionally built so a bare call (no `confirm`
argument) never deletes anything — it just reports back whether the target
is a file or directory. The correct sequence is:

1. Call `delete_file_or_dir(path)` with no `confirm` (or inspect it via
   `read_file`/`list_dir` first if you need to show the user what's inside).
2. Show the user what will be deleted and explicitly ask for confirmation —
   for a directory, `list_dir` it first so the user knows what they'd lose.
3. Only then call `delete_file_or_dir(path, confirm=True)` (or `confirm=False`
   if they decline).

Never infer `confirm=True` from general instructions like "clean up my
files" or "delete anything unused" — that phrase is not the same as the user
confirming a specific path. Get an explicit yes for the actual path(s) about
to be trashed. Deletion goes to the OS trash (recoverable), but still treat
it as a real destructive action, not a low-stakes one.

## Directory work

- `make_dir` is idempotent (`exist_ok=True`) — safe to call even if the
  directory might already exist; no need to `list_dir`-check first just to
  avoid an error.
- `list_dir` returns `data` as a list of `"Name: ... Type: ... Size: ..."`
  strings, one per entry, non-recursive. To explore a tree, walk it yourself
  by calling `list_dir` again on each subdirectory you find — don't assume
  it recurses.
- Use `list_dir` proactively before destructive or ambiguous operations
  (delete, overwrite into a directory you haven't seen) rather than acting
  blind and recovering from an error afterward.

## Moving, copying, and checking existence

- `move_file` and `copy_file` both validate *both* the source and the
  destination against the sandbox — a move/copy that would land outside the
  root is refused just like any other path escape.
- Neither one overwrites silently: if the destination already exists, the
  call fails unless you pass `overwrite=True`. Treat `overwrite=True` the
  same way you'd treat `write_file` over an existing file or a deletion —
  don't set it based on a vague instruction; confirm with the user first if
  the destination might hold something they care about, especially for
  `move_file` where the source is also being removed.
- Use `get_file_info` as the lightweight first move when you just need to
  know "does this exist, and is it a file or a directory" — e.g. before
  deciding whether `move_file`'s destination collision will trigger, or
  before choosing `read_file` vs `read_document`. Don't reach for a full
  `list_dir` of the parent or a `read_file` attempt just to answer that.
- "Rename" is the same operation as "move" here — same directory, different
  name in `destination`.

## Error handling patterns worth knowing

- A denied path (`ok=False`, escape-the-sandbox message) is not something to
  retry with a tweaked path — explain to the user that the path is outside
  the accessible workspace.
- Hidden files (dotfiles) and `.env` files are deliberately blocked by
  `read_file` as likely-confidential — don't try to route around this via
  `read_document` or shell-like tricks; treat the refusal as a hard rule
  about secrets, not an incidental limitation.
- On any `ok=False`, surface `message` to the user plainly rather than
  silently retrying the same call multiple times — most failures here
  (missing file, permission, wrong type) won't resolve themselves.

## Efficient multi-step workflows

Chain calls to avoid guesswork:

- "Edit this file" → `read_file`/`read_document` it, make the change in your
  own reasoning, then `write_file` the full new contents (there's no partial-
  edit tool here — every "edit" is read-modify-write of the whole file).
- "Move" or "rename" a file → use `move_file` directly; don't fall back to a
  manual read/write/delete sequence, since that needlessly routes binary or
  large files through text handling and adds an extra destructive delete
  step for no reason.
- "Duplicate"/"back up" a file before changing it → `copy_file` to a backup
  path, then edit the original — cheaper and safer than reading the whole
  file into context just to write it back out unchanged elsewhere.
- "Set up a project structure" → `make_dir` each directory, then `write_file`
  the initial files into them; no need to `list_dir` in between since
  `make_dir` won't error on existing dirs.
