from __future__ import annotations

import re
import subprocess
from pathlib import Path

from config import TARGET_PROJECT


SAFE_BRANCH_PATTERN = re.compile(
    r"^[A-Za-z0-9._/-]+$"
)


def _error(message: str, return_code: int = -1) -> dict:
    return {
        "success": False,
        "stdout": "",
        "stderr": message,
        "return_code": return_code,
    }


def _project_path() -> Path:
    return Path(TARGET_PROJECT).resolve()


def git_command(args: list[str]) -> dict:
    if not isinstance(args, list) or not args:
        return _error(
            "Git command arguments are required."
        )

    project_path = _project_path()

    if not project_path.exists():
        return _error(
            f"Target project does not exist: {project_path}"
        )

    if not project_path.is_dir():
        return _error(
            f"Target project is not a directory: {project_path}"
        )

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_path,
            shell=False,
            capture_output=True,
            text=True,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }

    except FileNotFoundError:
        return _error(
            "Git executable was not found."
        )

    except PermissionError:
        return _error(
            "Permission denied while executing Git."
        )

    except OSError as error:
        return _error(
            f"Operating system error while executing Git: {error}"
        )

    except Exception as error:
        return _error(
            f"Unexpected Git error: {error}"
        )


def status() -> dict:
    return git_command(
        ["status", "--short"]
    )


def diff() -> dict:
    return git_command(
        ["diff"]
    )


def staged_diff() -> dict:
    return git_command(
        ["diff", "--cached"]
    )


def current_branch() -> dict:
    return git_command(
        ["branch", "--show-current"]
    )


def create_branch(name: str) -> dict:
    if not isinstance(name, str) or not name.strip():
        return _error(
            "Branch name cannot be empty."
        )

    name = name.strip()

    if not SAFE_BRANCH_PATTERN.fullmatch(name):
        return _error(
            "Invalid Git branch name."
        )

    return git_command(
        ["checkout", "-b", name]
    )


def commit(message: str) -> dict:
    if not isinstance(message, str) or not message.strip():
        return _error(
            "Commit message cannot be empty."
        )

    message = message.strip()

    add_result = git_command(
        ["add", "-A"]
    )

    if not add_result["success"]:
        return add_result

    return git_command(
        ["commit", "-m", message]
    )


def head_commit() -> dict:
    return git_command(
        ["rev-parse", "HEAD"]
    )


def is_repository() -> bool:
    result = git_command(
        ["rev-parse", "--is-inside-work-tree"]
    )

    return (
        result["success"]
        and result["stdout"].strip().lower() == "true"
    )


def has_changes() -> bool:
    result = status()

    if not result["success"]:
        return False

    return bool(result["stdout"].strip())


def revert_to(commit_hash: str) -> dict:
    if not isinstance(commit_hash, str):
        return _error(
            "Commit hash must be a string."
        )

    commit_hash = commit_hash.strip()

    if not re.fullmatch(
        r"[0-9a-fA-F]{7,64}",
        commit_hash,
    ):
        return _error(
            "Invalid Git commit hash."
        )

    return git_command(
        ["reset", "--hard", commit_hash]
    )

