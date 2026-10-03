import os
import subprocess

from modules.toolkits.decorators import register_tool
from modules.toolkits.models import ToolResult  # adjust to wherever ToolResult lives

_TIMEOUT_SECONDS = 30


def _run_git(
    cwd_path: str, git_args: list[str], success_message: str
) -> ToolResult[str]:
    """Run a git command and wrap the outcome in a ToolResult."""
    if not os.path.isdir(cwd_path):
        return ToolResult(ok=False, message=f"Directory not found: {cwd_path}")

    try:
        result = subprocess.run(
            ["git", *git_args],
            cwd=cwd_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=_TIMEOUT_SECONDS,
        )
        return ToolResult(ok=True, message=success_message, data=result.stdout)
    except FileNotFoundError:
        return ToolResult(
            ok=False, message="'git' executable was not found on system PATH"
        )
    except subprocess.CalledProcessError as e:
        # git sometimes reports problems on stdout (e.g. "nothing to commit"), so keep both
        details = (e.stderr or "").strip() or (e.stdout or "").strip()
        return ToolResult(
            ok=False,
            message=f"git exited with code {e.returncode}",
            data=details,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok=False,
            message=f"git command timed out after {_TIMEOUT_SECONDS}s",
        )


@register_tool()
def git_status(path: str) -> ToolResult[str]:
    """Run `git status` in the given directory and return the result.

    On success, `data` is exactly what you'd see from running ``git status``
    in a terminal: branch info, staged/unstaged changes, untracked files.
    Read it directly to know what's going on. Present the full report in a
    table to the user.

    Args:
        path: The filesystem path of the git repository to check.

    Returns:
        A ToolResult. On success, ``data`` is raw stdout from ``git status``.
        On failure, ``ok`` is False, ``message`` describes what went wrong
        (git not found, non-zero exit, timeout), and ``data`` may hold git's
        error output.
    """
    return _run_git(path, ["status"], "git status completed")


@register_tool()
def git_add(cwd_path: str, file_path: str) -> ToolResult[str]:
    """Stage a file with `git add` inside a given repository.

    ``git add`` prints nothing unless something's wrong, so on success
    ``data`` is almost always empty. A success means "it's staged now, move on."

    Args:
        cwd_path: The working directory of the git repository.
        file_path: The path of the file to stage, relative to cwd_path.

    Returns:
        A ToolResult. On success, ``data`` is stdout from ``git add``
        (usually empty). On failure, ``ok`` is False and ``message`` describes
        what went wrong.
    """
    return _run_git(cwd_path, ["add", file_path], f"Staged {file_path}")


@register_tool()
def git_commit(cwd_path: str, commit_msg: str) -> ToolResult[str]:
    """Create a commit with the given message using `git commit`.

    On success, ``data`` tells you what was committed, e.g.
    "[main <hash>] <message>" plus a file-change summary. Read it to confirm
    the commit actually landed.

    Args:
        cwd_path: The working directory of the git repository.
        commit_msg: The commit message to use for the commit.

    Returns:
        A ToolResult. On success, ``data`` is stdout from ``git commit``.
        On failure, ``ok`` is False, ``message`` describes what went wrong,
        and ``data`` may hold git's output (e.g. "nothing to commit").
    """
    return _run_git(cwd_path, ["commit", "-m", commit_msg], "Commit created")


@register_tool()
def git_diff(cwd_path: str, file_path: str) -> ToolResult[str]:
    """Show the diff of a file using `git diff`.

    On success, ``data`` is the unified diff (lines with ``+``/``-`` prefixes).
    If there's no diff (file unchanged or already staged), ``data`` is an
    empty string. Read it to see exactly what changed line by line.

    Args:
        cwd_path: The working directory of the git repository.
        file_path: The path of the file to diff, relative to cwd_path.

    Returns:
        A ToolResult. On success, ``data`` is stdout from ``git diff``.
        On failure, ``ok`` is False and ``message`` describes what went wrong.
    """
    return _run_git(
        cwd_path, ["diff", file_path], f"git diff completed for {file_path}"
    )


@register_tool()
def git_restore(cwd_path: str, file_path: str, args: list[str]) -> ToolResult[str]:
    """Restore a file's contents using `git restore`.

    Restores ``file_path`` to match some source (by default, the index for
    the working tree, or HEAD for the index), discarding local changes
    according to the flags passed in ``args``. This is a potentially
    destructive operation: unstaged/uncommitted changes to the file can be
    permanently lost unless recoverable via ``--source`` or the git reflog.

    The resulting command is:
        git restore <args...> <file_path>

    e.g. args=["--staged"] runs `git restore --staged <file_path>`
         args=["--source=HEAD~1"] runs `git restore --source=HEAD~1 <file_path>`

    Args:
        cwd_path: The working directory of the git repository.
        file_path: The path of the file to restore, relative to cwd_path.
        args: Additional flags to pass to `git restore`, inserted before
              file_path on the command line. Common values include:
                - ``--staged`` / ``-S``: restore the index (unstage) instead
                  of the working tree.
                - ``--worktree`` / ``-W``: restore the working tree (default
                  target if neither this nor ``--staged`` is given).
                - ``--source=<commit>`` / ``-s <commit>``: restore from a
                  specific commit instead of the default source.
                - ``--ours`` / ``--theirs``: restore from a specific side of
                  an unresolved merge conflict.
              Do not use ``--patch``: it needs an interactive terminal and
              will hang until the timeout. Pass an empty list for default
              behavior (restore working tree from the index).

    Returns:
        A ToolResult. On success, ``data`` is stdout from `git restore`
        (typically empty). On failure, ``ok`` is False and ``message``
        describes what went wrong (invalid pathspec, unmerged conflict,
        timeout, etc.).

    Note:
        This mutates the working tree and/or index. Restored changes are not
        stashed, so confirm with the user before running it.
    """
    return _run_git(
        cwd_path,
        ["restore", *args, file_path],
        f"Restored {file_path}",
    )
