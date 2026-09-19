from typing import Any, TypedDict


class AgentState(TypedDict):
    task: str
    project_path: str
    plan: list[str]
    current_step: int
    repair_attempts: int
    files_changed: list[str]
    message: list[Any]
    output: str
    error: str | None
    test_output: str
    test_passed: bool
    finished: bool

