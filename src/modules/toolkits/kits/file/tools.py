import shutil
from pathlib import Path

import pymupdf
import pymupdf4llm
from send2trash import send2trash

from modules.toolkits.decorators import register_tool
from modules.toolkits.models import ToolResult


def validate_path(target: str) -> tuple[bool, str]:
    """Resolves a path and blocks anything unsafe.

    Returns (True, resolved_path_str) on success, or (False, denial_message)
    if the path escapes the working directory or points at a hidden/env file.
    """
    root = Path.cwd().resolve()
    target_path = (root / target).resolve()

    if not target_path.is_relative_to(root):
        return False, f"Access denied: '{target}' attempts to escape working directory."

    rel = target_path.relative_to(root)
    if any(part.startswith(".") for part in rel.parts) or target_path.suffix == ".env":
        return False, f"Access denied: '{target}' is a hidden or confidential file."

    return True, str(target_path)


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _overlaps(a: Path, b: Path) -> bool:
    return a.is_relative_to(b) or b.is_relative_to(a)


@register_tool()
def read_file(path: str) -> ToolResult[str]:
    """Reads and returns the full text contents of a file at the given path.

    Use this to inspect a file's contents before editing, summarizing, or
    answering questions about what it contains. Fails if the file does not
    exist or cannot be read due to permissions.
    """
    success, target_str = validate_path(path)
    if not success:
        return ToolResult(ok=False, message=target_str)
    try:
        content = Path(target_str).read_text(encoding="utf-8")
        return ToolResult(ok=True, message="File read successfully", data=content)
    except FileNotFoundError:
        return ToolResult(ok=False, message=f"File does not exist: '{path}'")
    except PermissionError:
        return ToolResult(ok=False, message=f"Permission denied for '{path}'")
    except IsADirectoryError:
        return ToolResult(ok=False, message=f"'{path}' is a directory, not a file")
    except UnicodeDecodeError:
        return ToolResult(
            ok=False, message="File is not valid UTF-8 text (likely a binary file)"
        )


@register_tool()
def read_document(path: str) -> ToolResult[str]:
    """Reads a PDF or DOCX file and returns its contents as markdown.

    Use this to inspect a document before summarizing or answering questions
    about it. Fails if the file does not exist or cannot be read.
    """
    success, target_str = validate_path(path)
    if not success:
        return ToolResult(ok=False, message=target_str)

    if Path(target_str).suffix.lower() not in (".pdf", ".docx"):
        return ToolResult(ok=False, message="Only .pdf and .docx files are supported")

    try:
        text = pymupdf4llm.to_markdown(target_str, page_chunks=False)
    except pymupdf.FileNotFoundError:
        return ToolResult(ok=False, message=f"File does not exist: '{path}'")
    except pymupdf.FileDataError:
        return ToolResult(ok=False, message=f"'{path}' is corrupt or unreadable")
    except PermissionError:
        return ToolResult(ok=False, message=f"Permission denied for '{path}'")

    if not isinstance(text, str):
        return ToolResult(ok=False, message="Unexpected extractor output type")

    return ToolResult(ok=True, message="Document read successfully", data=text)


# WARNING: this overwrites the file. Use append_file to add to an existing one.
@register_tool()
def write_file(path: str, content: str) -> ToolResult[str]:
    """Creates a new file or completely overwrites an existing file with the given content.

    Any existing content at this path will be permanently replaced. Use
    append_file instead if you want to add to an existing file without
    erasing what's already there.
    """
    success, target_str = validate_path(path)
    if not success:
        return ToolResult(ok=False, message=target_str)
    try:
        Path(target_str).write_text(content, encoding="utf-8")
        return ToolResult(ok=True, message="File written successfully")
    except PermissionError:
        return ToolResult(ok=False, message=f"Permission denied for '{path}'")
    except FileNotFoundError:
        return ToolResult(ok=False, message="Parent directory does not exist")
    except IsADirectoryError:
        return ToolResult(ok=False, message=f"'{path}' is a directory, not a file")
    except NotADirectoryError:
        return ToolResult(
            ok=False, message=f"A component of '{path}' is a file, not a directory"
        )


@register_tool()
def append_file(path: str, content: str) -> ToolResult[str]:
    """Appends content to the end of an existing file without modifying what's already there.

    The target file must already exist. Use write_file to create it first if
    it doesn't.
    """
    success, target_str = validate_path(path)
    if not success:
        return ToolResult(ok=False, message=target_str)
    target = Path(target_str)
    if not target.exists():
        return ToolResult(ok=False, message="File does not exist")
    try:
        with open(target, "a", encoding="utf-8") as file:
            file.write(content)
        return ToolResult(ok=True, message="Content appended successfully")
    except PermissionError:
        return ToolResult(ok=False, message=f"Permission denied for '{path}'")
    except IsADirectoryError:
        return ToolResult(ok=False, message=f"'{path}' is a directory, not a file")


@register_tool()
def make_dir(path: str, parents: bool = True) -> ToolResult[str]:
    """Creates a new directory at the given path.

    If parents is True (default), any missing parent directories are created
    automatically. Succeeds silently if the directory already exists.
    """
    success, target_str = validate_path(path)
    if not success:
        return ToolResult(ok=False, message=target_str)
    try:
        Path(target_str).mkdir(parents=parents, exist_ok=True)
        return ToolResult(ok=True, message="Directory created")
    except PermissionError:
        return ToolResult(ok=False, message=f"Permission denied for '{path}'")
    except FileNotFoundError:
        return ToolResult(
            ok=False, message="Parent directory does not exist and parents=False"
        )
    except FileExistsError:
        return ToolResult(ok=False, message=f"'{path}' already exists as a file")
    except NotADirectoryError:
        return ToolResult(
            ok=False, message=f"A component of '{path}' is a file, not a directory"
        )


@register_tool()
def list_dir(starting_path: str) -> ToolResult[list[str]]:
    """Lists the contents of a directory, showing each entry's name, type, and size.

    Use this to explore a directory's structure before deciding which files
    to read, write, or delete. Hidden entries are not shown.
    """
    success, target_str = validate_path(starting_path)
    if not success:
        return ToolResult(ok=False, message=target_str)
    try:
        entries: list[str] = []
        for entry in sorted(Path(target_str).iterdir()):
            if entry.name.startswith("."):
                continue
            kind = "dir" if entry.is_dir() else "file"
            size = entry.stat().st_size if entry.is_file() else "-"
            entries.append(f"Name: {entry.name} Type: {kind} Size: {size}")

        message = (
            "Directory is empty" if not entries else "Directory listed successfully"
        )
        return ToolResult(ok=True, message=message, data=entries)
    except FileNotFoundError:
        return ToolResult(ok=False, message="Path does not exist")
    except PermissionError:
        return ToolResult(ok=False, message=f"Permission denied for '{starting_path}'")
    except NotADirectoryError:
        return ToolResult(
            ok=False, message=f"'{starting_path}' is a file, not a directory"
        )


@register_tool()
def move_file(
    source: str, destination: str, overwrite: bool = False
) -> ToolResult[str]:
    """Moves or renames a file or directory from source to destination.

    Fails if the source doesn't exist, or if the destination already exists
    and overwrite is not True. Overwriting destroys whatever is at the
    destination, so confirm with the user before passing overwrite=True.
    """
    src_ok, src_str = validate_path(source)
    if not src_ok:
        return ToolResult(ok=False, message=src_str)
    dst_ok, dst_str = validate_path(destination)
    if not dst_ok:
        return ToolResult(ok=False, message=dst_str)

    src, dst = Path(src_str), Path(dst_str)

    if not src.exists():
        return ToolResult(ok=False, message=f"'{source}' does not exist")
    if _overlaps(src, dst):
        return ToolResult(
            ok=False, message="Source and destination are the same or nested"
        )
    if dst.exists() and not overwrite:
        return ToolResult(
            ok=False,
            message=f"'{destination}' already exists. Pass overwrite=True to replace it, after confirming with the user.",
        )
    try:
        if dst.exists():
            _remove(dst)
        shutil.move(str(src), str(dst))
        return ToolResult(ok=True, message=f"Moved '{source}' to '{destination}'")
    except PermissionError:
        return ToolResult(
            ok=False, message=f"Permission denied for '{source}' or '{destination}'"
        )
    except FileNotFoundError:
        return ToolResult(
            ok=False, message="Parent directory of destination does not exist"
        )
    except OSError as e:
        return ToolResult(ok=False, message=f"Failed to move '{source}': {e}")


@register_tool()
def copy_file(
    source: str, destination: str, overwrite: bool = False
) -> ToolResult[str]:
    """Copies a file or directory from source to destination, leaving the original in place.

    Fails if the source doesn't exist, or if the destination already exists
    and overwrite is not True.
    """
    src_ok, src_str = validate_path(source)
    if not src_ok:
        return ToolResult(ok=False, message=src_str)
    dst_ok, dst_str = validate_path(destination)
    if not dst_ok:
        return ToolResult(ok=False, message=dst_str)

    src, dst = Path(src_str), Path(dst_str)

    if not src.exists():
        return ToolResult(ok=False, message=f"'{source}' does not exist")
    if _overlaps(src, dst):
        return ToolResult(
            ok=False, message="Source and destination are the same or nested"
        )
    if dst.exists() and not overwrite:
        return ToolResult(
            ok=False,
            message=f"'{destination}' already exists. Pass overwrite=True to replace it, after confirming with the user.",
        )
    try:
        if dst.exists():
            _remove(dst)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return ToolResult(ok=True, message=f"Copied '{source}' to '{destination}'")
    except PermissionError:
        return ToolResult(
            ok=False, message=f"Permission denied for '{source}' or '{destination}'"
        )
    except FileNotFoundError:
        return ToolResult(
            ok=False, message="Parent directory of destination does not exist"
        )
    except OSError as e:
        return ToolResult(ok=False, message=f"Failed to copy '{source}': {e}")


@register_tool()
def get_file_info(path: str) -> ToolResult[dict[str, object]]:
    """Returns metadata about a file or directory: whether it exists, its type, and size.

    Use this as a lightweight existence/type check before deciding whether to
    read, write, move, or delete something.
    """
    success, target_str = validate_path(path)
    if not success:
        return ToolResult(ok=False, message=target_str)
    target = Path(target_str)
    try:
        if not target.exists():
            return ToolResult(
                ok=True, message="Path does not exist", data={"exists": False}
            )
        info: dict[str, object] = {
            "exists": True,
            "type": "dir" if target.is_dir() else "file",
            "size": target.stat().st_size if target.is_file() else None,
        }
        return ToolResult(ok=True, message="File info retrieved", data=info)
    except PermissionError:
        return ToolResult(ok=False, message=f"Permission denied for '{path}'")


@register_tool()
def delete_file_or_dir(path: str, confirm: bool | None = None) -> ToolResult[str]:
    """Moves a file or directory to the trash (recoverable, not permanent deletion).

    This is destructive and requires explicit user confirmation. Call this
    tool first with confirm left unset to see what's being deleted. Only pass
    confirm=True after the user has explicitly agreed, or confirm=False if
    they decline.
    """
    success, target_str = validate_path(path)
    if not success:
        return ToolResult(ok=False, message=target_str)
    target = Path(target_str)

    if target == Path.cwd().resolve():
        return ToolResult(ok=False, message="Refusing to delete the working directory")
    if not target.exists():
        return ToolResult(ok=False, message=f"'{path}' does not exist")

    if confirm is None:
        kind = "directory" if target.is_dir() else "file"
        return ToolResult(
            ok=False,
            message=f"'{path}' is a {kind}. Check its contents, ask the user to confirm, then call again with confirm=True.",
        )
    if not confirm:
        return ToolResult(ok=False, message="The user denied the request for deletion")

    try:
        send2trash(target_str)
    except OSError as e:
        return ToolResult(ok=False, message=f"Failed to move '{path}' to trash: {e}")
    return ToolResult(ok=True, message=f"'{path}' was moved to the trash")
