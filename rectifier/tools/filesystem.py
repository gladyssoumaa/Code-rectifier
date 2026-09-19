from __future__ import annotations

from pathlib import Path

from config import (
    TARGET_PROJECT,
    IGNORED_DIRECTORIES,
    IGNORED_FILES,
)


def _project_root() -> Path:
    project = Path(TARGET_PROJECT).resolve()

    if not project.exists():
        raise FileNotFoundError(
            f"Target project does not exist: {project}"
        )

    if not project.is_dir():
        raise ValueError(
            f"Target project is not a directory: {project}"
        )

    return project


def resolve_path(path: str) -> Path:
    if not isinstance(path, str):
        raise TypeError(
            "Path must be a string."
        )

    path = path.strip()

    if not path:
        raise ValueError(
            "Path cannot be empty."
        )

    project = _project_root()
    candidate = Path(path)

    if candidate.is_absolute():
        raise ValueError(
            "Absolute paths are not allowed."
        )

    target = (project / candidate).resolve()

    if target != project and project not in target.parents:
        raise ValueError(
            "Path is outside the target project."
        )

    return target


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


def list_files(
    directory: str = ".",
) -> list[str]:
    if not directory or not directory.strip():
        directory = "."
        
    project = _project_root()
    root = resolve_path(directory)

    if not root.exists():
        raise FileNotFoundError(directory)

    if not root.is_dir():
        raise ValueError(
            f"{directory} is not a directory."
        )

    files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if _is_ignored(path, project):
            continue

        files.append(
            str(path.relative_to(project))
        )

    return sorted(files)


def read_file(path: str) -> str:
    project = _project_root()
    file_path = resolve_path(path)

    if not file_path.exists():
        raise FileNotFoundError(path)

    if not file_path.is_file():
        raise ValueError(
            f"{path} is not a file."
        )

    if _is_ignored(file_path, project):
        raise ValueError(
            f"Access to ignored file is not allowed: {path}"
        )

    return file_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def write_file(
    path: str,
    content: str,
) -> str:
    project = _project_root()
    file_path = resolve_path(path)

    if not isinstance(content, str):
        raise TypeError(
            "File content must be a string."
        )

    if _is_ignored(file_path, project):
        raise ValueError(
            f"Writing to ignored file is not allowed: {path}"
        )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )

    return str(
        file_path.relative_to(project)
    )


def delete_file(path: str) -> str:
    project = _project_root()
    file_path = resolve_path(path)

    if not file_path.exists():
        raise FileNotFoundError(path)

    if not file_path.is_file():
        raise ValueError(
            f"{path} is not a file."
        )

    if _is_ignored(file_path, project):
        raise ValueError(
            f"Deleting ignored files is not allowed: {path}"
        )

    file_path.unlink()

    return str(
        file_path.relative_to(project)
    )


def file_exists(path: str) -> bool:
    return resolve_path(path).exists()

