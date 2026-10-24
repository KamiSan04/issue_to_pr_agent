import shlex
import subprocess
from pathlib import Path

WORKSPACE = Path("workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)

ALLOWED_GIT = {"status", "diff", "log", "branch", "add", "commit", "checkout"}
MAX_CHARS = 8000


def _safe_path(relative: str) -> Path:
    path = (WORKSPACE / relative).resolve()
    if not path.is_relative_to(WORKSPACE):
        raise ValueError("Path is outside the workspace.")
    if ".git" in path.relative_to(WORKSPACE).parts:
        raise ValueError("The .git folder is off limits.")
    return path


def list_files(folder: str = ".") -> str:
    """Lists the files and folders inside a workspace folder."""
    try:
        path = _safe_path(folder)
        names = sorted(
            item.name + ("/" if item.is_dir() else "") for item in path.iterdir()
        )
    except (OSError, ValueError) as error:
        return f"Error: {error}"
    return "\n".join(names) if names else "(empty folder)"


def read_file(path: str) -> str:
    """Reads a text file from the workspace."""
    try:
        text = _safe_path(path).read_text(encoding="utf-8")
    except (OSError, ValueError, UnicodeDecodeError) as error:
        return f"Error: {error}"
    return text[:MAX_CHARS]


def write_file(path: str, content: str) -> str:
    """Writes text to a workspace file. Creates or overwrites it."""
    try:
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except (OSError, ValueError) as error:
        return f"Error: {error}"
    return f"Wrote {len(content)} characters to {path}"


def run_git(args: str) -> str:
    """Runs a git command in the workspace. Allowed: status, diff, log, branch, add, commit, checkout."""
    try:
        parts = shlex.split(args)
    except ValueError as error:
        return f"Error: {error}"
    if not parts or parts[0] not in ALLOWED_GIT:
        return "Error: git command not allowed."
    if any(part.startswith("--output") for part in parts):
        return "Error: that git option is not allowed."
    try:
        result = subprocess.run(
            ["git", *parts],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"Error: {error}"
    return (result.stdout + result.stderr)[:MAX_CHARS] or "(no output)"


TOOL_FUNCTIONS = [list_files, read_file, write_file, run_git]
TOOLS = {function.__name__: function for function in TOOL_FUNCTIONS}