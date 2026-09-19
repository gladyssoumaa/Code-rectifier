from __future__ import annotations
from dotenv import load_dotenv 

import os
from pathlib import Path

load_dotenv()

TARGET_PROJECT = Path(
    os.getenv("TARGET_PROJECT", ".")
).expanduser().resolve()


TASK = os.getenv(
    "CODE_RECTIFIER_TASK",
    """
Monitor the target API project for software failures.

When tests fail:
1. Inspect the project structure.
2. Identify the failing endpoint or source file.
3. Diagnose the root cause using the actual error output.
4. Search relevant documentation when necessary.
5. Make the smallest appropriate code change.
6. Run the tests again.
7. Continue repairing until the tests pass or the repair limit is reached.
""".strip(),
)


TEST_COMMAND = os.getenv(
    "TEST_COMMAND",
    "pytest",
).strip()


COMMAND_TIMEOUT = int(
    os.getenv("COMMAND_TIMEOUT", "120")
)


DEFAULT_ALLOWED_COMMANDS = {
    "python",
    "python3",
    "pytest",
}


def _parse_allowed_commands() -> set[str]:
    value = os.getenv("ALLOWED_COMMANDS", "").strip()

    if not value:
        return set(DEFAULT_ALLOWED_COMMANDS)

    commands = {
        command.strip()
        for command in value.split(",")
        if command.strip()
    }

    return commands or set(DEFAULT_ALLOWED_COMMANDS)


ALLOWED_COMMANDS = _parse_allowed_commands()


GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    "",
).strip()


GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
).strip()


GROQ_SEARCH_MODEL = os.getenv(
    "GROQ_SEARCH_MODEL",
    GROQ_MODEL,
).strip()


GROQ_TEMPERATURE = float(
    os.getenv("GROQ_TEMPERATURE", "0.1")
)


GROQ_MAX_TOKENS = int(
    os.getenv("GROQ_MAX_TOKENS", "4096")
)


MAX_AGENT_ITERATIONS = int(
    os.getenv("MAX_AGENT_ITERATIONS", "15")
)


MAX_REPAIR_ATTEMPTS = int(
    os.getenv("MAX_REPAIR_ATTEMPTS", "3")
)


WATCH_INTERVAL = float(
    os.getenv("WATCH_INTERVAL", "1.0")
)


DEBOUNCE_SECONDS = float(
    os.getenv("DEBOUNCE_SECONDS", "2.0")
)


IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
}


IGNORED_FILES = {
    ".DS_Store",
    "Thumbs.db",
    ".gitignore",
}


MAX_SEARCH_RESULTS = int(
    os.getenv("MAX_SEARCH_RESULTS", "5")
)


def validate_config() -> None:
    if not TARGET_PROJECT.exists():
        raise ValueError(
            f"TARGET_PROJECT does not exist: {TARGET_PROJECT}"
        )

    if not TARGET_PROJECT.is_dir():
        raise ValueError(
            f"TARGET_PROJECT is not a directory: {TARGET_PROJECT}"
        )

    if not TEST_COMMAND:
        raise ValueError(
            "TEST_COMMAND cannot be empty."
        )

    if COMMAND_TIMEOUT <= 0:
        raise ValueError(
            "COMMAND_TIMEOUT must be greater than zero."
        )

    if not ALLOWED_COMMANDS:
        raise ValueError(
            "ALLOWED_COMMANDS cannot be empty."
        )

    if MAX_AGENT_ITERATIONS <= 0:
        raise ValueError(
            "MAX_AGENT_ITERATIONS must be greater than zero."
        )

    if MAX_REPAIR_ATTEMPTS <= 0:
        raise ValueError(
            "MAX_REPAIR_ATTEMPTS must be greater than zero."
        )

    if GROQ_TEMPERATURE < 0:
        raise ValueError(
            "GROQ_TEMPERATURE cannot be negative."
        )

    if GROQ_MAX_TOKENS <= 0:
        raise ValueError(
            "GROQ_MAX_TOKENS must be greater than zero."
        )

    if MAX_SEARCH_RESULTS <= 0:
        raise ValueError(
            "MAX_SEARCH_RESULTS must be greater than zero."
        )


def get_config_summary() -> dict:
    return {
        "target_project": str(TARGET_PROJECT),
        "test_command": TEST_COMMAND,
        "command_timeout": COMMAND_TIMEOUT,
        "allowed_commands": sorted(ALLOWED_COMMANDS),
        "groq_model": GROQ_MODEL,
        "groq_search_model": GROQ_SEARCH_MODEL,
        "groq_temperature": GROQ_TEMPERATURE,
        "groq_max_tokens": GROQ_MAX_TOKENS,
        "max_agent_iterations": MAX_AGENT_ITERATIONS,
        "max_repair_attempts": MAX_REPAIR_ATTEMPTS,
        "watch_interval": WATCH_INTERVAL,
        "debounce_seconds": DEBOUNCE_SECONDS,
        "max_search_results": MAX_SEARCH_RESULTS,
        "groq_api_key_configured": bool(GROQ_API_KEY),
    }


if __name__ == "__main__":
    try:
        validate_config()

        print("Code Rectifier configuration is valid.")

        for key, value in get_config_summary().items():
            print(f"{key}: {value}")

    except ValueError as error:
        print(f"Configuration error: {error}")
        raise SystemExit(1)

