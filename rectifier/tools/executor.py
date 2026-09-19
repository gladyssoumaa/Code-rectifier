from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from config import (
    TARGET_PROJECT,
    COMMAND_TIMEOUT,
    ALLOWED_COMMANDS,
)


BLOCKED_SHELL_TOKENS = {
    ";",
    "&&",
    "||",
    "|",
    ">",
    ">>",
    "<",
    "<<",
    "`",
    "$(",
    "${",
}


def _error(message: str, return_code: int = -1) -> dict:
    return {
        "success": False,
        "stdout": "",
        "stderr": message,
        "return_code": return_code,
    }


def _normalise_allowed_commands() -> set[str]:
    return {
        str(command).strip()
        for command in ALLOWED_COMMANDS
        if str(command).strip()
    }


def _contains_blocked_shell_syntax(command: str) -> str | None:
    for token in BLOCKED_SHELL_TOKENS:
        if token in command:
            return token

    return None


def _parse_command(command: str) -> list[str] | None:
    try:
        return shlex.split(command)
    except ValueError:
        return None


def run_command(
    command: str,
    timeout: int = COMMAND_TIMEOUT,
) -> dict:
    if not isinstance(command, str):
        return _error("Command must be a string.")

    command = command.strip()

    if not command:
        return _error("No command provided.")

    blocked_token = _contains_blocked_shell_syntax(command)

    if blocked_token:
        return _error(
            f"Shell syntax '{blocked_token}' is not allowed."
        )

    args = _parse_command(command)

    if not args:
        return _error("Invalid command syntax.")

    executable = args[0]

    allowed_commands = _normalise_allowed_commands()

    if executable not in allowed_commands:
        return _error(
            f"Command not allowed: {executable}. "
            f"Allowed commands: {', '.join(sorted(allowed_commands))}"
        )

    project_path = Path(TARGET_PROJECT).resolve()

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
            args,
            shell=False,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }

    except FileNotFoundError:
        return _error(
            f"Executable not found: {executable}"
        )

    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")

        return {
            "success": False,
            "stdout": stdout,
            "stderr": (
                f"Command timed out after {timeout} seconds.\n"
                f"{stderr}"
            ),
            "return_code": -1,
        }

    except PermissionError:
        return _error(
            f"Permission denied while executing: {executable}"
        )

    except OSError as error:
        return _error(
            f"Operating system error while executing command: {error}"
        )

    except Exception as error:
        return _error(
            f"Unexpected command execution error: {error}"
        )

