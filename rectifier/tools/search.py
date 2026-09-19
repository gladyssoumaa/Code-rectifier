from __future__ import annotations

from pathlib import Path

from config import (
    TARGET_PROJECT,
    IGNORED_DIRECTORIES,
    IGNORED_FILES,
    GROQ_API_KEY,
    GROQ_SEARCH_MODEL,
)
from tools.filesystem import resolve_path

from groq import Groq


def _is_ignored(
    path: Path,
    project: Path,
) -> bool:
    relative = path.relative_to(project)

    if any(
        part in IGNORED_DIRECTORIES
        for part in relative.parts
    ):
        return True

    if path.name in IGNORED_FILES:
        return True

    return False


def search_files(
    query: str,
    directory: str = ".",
    case_sensitive: bool = False,
) -> list[dict]:
    project = Path(TARGET_PROJECT).resolve()
    root = resolve_path(directory)

    if not root.exists():
        raise FileNotFoundError(directory)

    if not root.is_dir():
        raise ValueError(
            f"{directory} is not a directory."
        )

    if not query:
        return []

    search_query = (
        query
        if case_sensitive
        else query.lower()
    )

    results = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if _is_ignored(path, project):
            continue

        try:
            content = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        comparison_content = (
            content
            if case_sensitive
            else content.lower()
        )

        if search_query not in comparison_content:
            continue

        lines = content.splitlines()
        matches = []

        for number, line in enumerate(
            lines,
            start=1,
        ):
            comparison = (
                line
                if case_sensitive
                else line.lower()
            )

            if search_query in comparison:
                matches.append({
                    "line": number,
                    "content": line.strip(),
                })

        results.append({
            "file": str(
                path.relative_to(project)
            ),
            "matches": matches,
        })

    return results


def find_files(
    pattern: str,
    directory: str = ".",
) -> list[str]:
    project = Path(TARGET_PROJECT).resolve()
    root = resolve_path(directory)

    if not root.exists():
        raise FileNotFoundError(directory)

    if not root.is_dir():
        raise ValueError(
            f"{directory} is not a directory."
        )

    results = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if _is_ignored(path, project):
            continue

        if path.match(pattern):
            results.append(
                str(path.relative_to(project))
            )

    return sorted(results)


_client = (
    Groq(api_key=GROQ_API_KEY)
    if GROQ_API_KEY
    else None
)


def web_search(query: str) -> str:
    if not query:
        return "SEARCH ERROR: Empty search query."

    if _client is None:
        return "SEARCH ERROR: GROQ_API_KEY is not configured."

    try:
        response = _client.chat.completions.create(
            model=GROQ_SEARCH_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Explain how to understand or resolve the "
                        "following software problem. Provide a concise "
                        "technical explanation and, where appropriate, "
                        "a code example.\n\n"
                        f"{query}"
                    ),
                }
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content

        return content or "No search result returned."

    except Exception as error:
        return f"SEARCH ERROR: {error}"

