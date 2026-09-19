from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from groq import Groq
from langgraph.graph import END, START, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage

from config import (
    GROQ_API_KEY,
    GROQ_MAX_TOKENS,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    MAX_REPAIR_ATTEMPTS,
    TEST_COMMAND,
    TARGET_PROJECT,
)
from state import AgentState
from tools.executor import run_command
from tools.filesystem import list_files, read_file, write_file
from tools.search import search_files, web_search


client = Groq(api_key=GROQ_API_KEY)

MAX_CONTEXT_FILES = 12
MAX_FILE_CHARS = 9000
MAX_TEST_OUTPUT = 10000
MAX_REPAIR_CONTEXT = 6
RATE_LIMIT_WAIT = 5


def _print(message: str) -> None:
    print(f"[Code Rectifier] {message}")


def _trim(value: str, limit: int) -> str:
    if not value:
        return ""

    if len(value) <= limit:
        return value

    return value[:limit] + "\n...[truncated]"


def _is_relevant_file(path: str) -> bool:
    path_lower = path.lower()

    relevant_names = {
        "main.py",
        "app.py",
        "api.py",
        "server.py",
        "routes.py",
        "router.py",
        "auth.py",
        "security.py",
        "config.py",
        "settings.py",
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "manage.py",
        "conftest.py",
    }

    name = Path(path).name.lower()

    if name in relevant_names:
        return True

    keywords = (
        "route",
        "router",
        "endpoint",
        "api",
        "auth",
        "security",
        "test",
        "model",
        "schema",
        "service",
        "controller",
    )

    if any(keyword in path_lower for keyword in keywords):
        return True

    return path_lower.endswith(
        (
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
        )
    )


def _select_context_files(files: list[str]) -> list[str]:
    relevant = [
        path
        for path in files
        if _is_relevant_file(path)
    ]

    if not relevant:
        relevant = files

    priority = []

    for path in relevant:
        name = Path(path).name.lower()

        score = 0

        if name in {
            "main.py",
            "app.py",
            "api.py",
            "server.py",
        }:
            score += 100

        if "route" in name or "router" in name:
            score += 80

        if "auth" in name or "security" in name:
            score += 70

        if "test" in name:
            score += 60

        if name in {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
        }:
            score += 50

        priority.append((score, path))

    priority.sort(
        key=lambda item: (-item[0], item[1])
    )

    return [
        path
        for _, path in priority[:MAX_CONTEXT_FILES]
    ]


def _collect_project_context(
    files: list[str],
    test_output: str = "",
    changed_files: list[str] | None = None,
) -> str:
    selected = _select_context_files(files)

    if changed_files:
        for changed in changed_files:
            if changed in files and changed not in selected:
                selected.append(changed)

        selected = selected[:MAX_CONTEXT_FILES]

    sections = []

    sections.append(
        "PROJECT FILES:\n"
        + "\n".join(files)
    )

    if test_output:
        sections.append(
            "TEST OUTPUT:\n"
            + _trim(test_output, MAX_TEST_OUTPUT)
        )

    for path in selected:
        try:
            content = read_file(path)
        except Exception as error:
            content = f"Unable to read file: {error}"

        sections.append(
            f"FILE: {path}\n"
            f"{_trim(content, MAX_FILE_CHARS)}"
        )

    return "\n\n".join(sections)


def _call_model(
    messages: list[Any],
    tools: list[dict] | None = None,
    tool_choice: Any = "auto",
):
    kwargs = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": GROQ_TEMPERATURE,
        "max_tokens": GROQ_MAX_TOKENS,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    for attempt in range(2):
        try:
            return client.chat.completions.create(**kwargs)

        except Exception as error:
            error_text = str(error)

            if "429" not in error_text:
                raise

            if attempt == 1:
                raise

            _print(
                f"Groq rate limit encountered. "
                f"Waiting {RATE_LIMIT_WAIT} seconds..."
            )

            time.sleep(RATE_LIMIT_WAIT)

    raise RuntimeError("Unable to contact Groq.")


WRITE_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": (
            "Create or replace a project file with the supplied "
            "complete file contents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Project-relative file path."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Complete contents of the file."
                    ),
                },
            },
            "required": [
                "path",
                "content",
            ],
        },
    },
}


SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": (
            "Search the target project for a text string."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                },
            },
            "required": [
                "query",
            ],
        },
    },
}


WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Retrieve technical information relevant to the "
            "software problem."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                },
            },
            "required": [
                "query",
            ],
        },
    },
}


def _repair_system_prompt() -> str:
    return """
You are Code Rectifier, an autonomous software repair agent.

Your job is to implement the user's task in the target project.

You have already been given:
- the project file list
- relevant source files
- test output when available
- previous repair information when available

Do not spend the response repeatedly inspecting files.

Reason about the task and implement the required change.

Rules:
1. Diagnose the actual problem from the supplied project context.
2. Make the smallest correct changes.
3. Use write_file to modify files.
4. You may use search_files only when the supplied context is genuinely insufficient.
5. Use web_search only when external technical information is genuinely necessary.
6. Do not modify unrelated files.
7. Preserve existing application behaviour unless the task requires a change.
8. If authentication is requested, protect every applicable API endpoint.
9. Ensure any new authentication endpoint is actually registered.
10. After making changes, stop and allow the verification stage to run tests.
11. Never merely describe the fix when you can implement it.
12. Do not output a proposed patch as prose. Use write_file.
""".strip()


def _repair(
    state: AgentState,
) -> AgentState:
    attempt = state["repair_attempts"] + 1

    _print(
        f"Starting repair attempt "
        f"{attempt}/{MAX_REPAIR_ATTEMPTS}."
    )

    project_files = list_files(".")

    context = _collect_project_context(
        project_files,
        state.get("test_output", ""),
        state.get("files_changed", []),
    )

    task = state["task"]

    previous_error = state.get("error") or ""

    prompt = f"""
USER TASK:
{task}

REPAIR ATTEMPT:
{attempt}

PREVIOUS ERROR:
{_trim(previous_error, 6000)}

CURRENT PROJECT CONTEXT:
{context}

Implement the user's task now.

If files must be changed, call write_file for each changed file.
Return no implementation explanation until after the required file
changes have been made.
""".strip()

    messages = [
        SystemMessage(
            content=_repair_system_prompt()
        ),
        HumanMessage(
            content=prompt
        ),
    ]

    _print("Sending focused repair request to Groq...")

    response = _call_model(
        messages,
        tools=[
            WRITE_FILE_TOOL,
            SEARCH_TOOL,
            WEB_SEARCH_TOOL,
        ],
        tool_choice="auto",
    )

    changed_files = list(
        state.get("files_changed", [])
    )

    tool_calls = response.choices[0].message.tool_calls or []

    _print(
        f"Model returned {len(tool_calls)} tool call(s)."
    )

    for tool_call in tool_calls:
        function_name = tool_call.function.name

        try:
            arguments = json.loads(
                tool_call.function.arguments
            )
        except json.JSONDecodeError:
            _print(
                f"Invalid arguments returned for "
                f"{function_name}."
            )
            continue

        if function_name == "write_file":
            path = arguments.get("path")
            content = arguments.get("content")

            if not isinstance(path, str):
                continue

            if not isinstance(content, str):
                continue

            try:
                written = write_file(
                    path,
                    content,
                )

                if written not in changed_files:
                    changed_files.append(written)

                _print(
                    f"File changed: {written}"
                )

            except Exception as error:
                _print(
                    f"Unable to write {path}: {error}"
                )

        elif function_name == "search_files":
            query = arguments.get("query", "")

            try:
                results = search_files(query)

                _print(
                    f"Search returned {len(results)} result(s)."
                )

            except Exception as error:
                _print(
                    f"Search failed: {error}"
                )

        elif function_name == "web_search":
            query = arguments.get("query", "")

            try:
                result = web_search(query)

                _print(
                    "Technical search completed."
                )

            except Exception as error:
                _print(
                    f"Technical search failed: {error}"
                )

    output = response.choices[0].message.content or ""

    return {
        **state,
        "repair_attempts": attempt,
        "files_changed": changed_files,
        "output": output,
        "error": None,
        "finished": False,
    }


def _verify(
    state: AgentState,
) -> AgentState:
    _print(
        f"Running verification: {TEST_COMMAND}"
    )

    result = run_command(
        TEST_COMMAND
    )

    output = "\n".join(
        part
        for part in [
            result.get("stdout", ""),
            result.get("stderr", ""),
        ]
        if part
    )

    passed = bool(
        result.get("success")
    )

    if passed:
        _print("Verification PASSED.")
    else:
        _print("Verification FAILED.")

    return {
        **state,
        "test_output": _trim(
            output,
            MAX_TEST_OUTPUT,
        ),
        "test_passed": passed,
        "error": None if passed else output,
        "finished": passed,
    }


def _route_after_verification(
    state: AgentState,
) -> str:
    if state.get("test_passed"):
        return "done"

    if (
        state.get("repair_attempts", 0)
        >= MAX_REPAIR_ATTEMPTS
    ):
        return "done"

    return "repair"


def _prepare_context(
    state: AgentState,
) -> AgentState:
    _print("Starting project inspection.")

    files = list_files(".")

    _print(
        f"Found {len(files)} project files."
    )

    test_result = run_command(
        TEST_COMMAND
    )

    test_output = "\n".join(
        part
        for part in [
            test_result.get("stdout", ""),
            test_result.get("stderr", ""),
        ]
        if part
    )

    if test_result.get("success"):
        _print(
            "Initial verification passed. "
            "Proceeding with the requested task."
        )
    else:
        _print(
            "Initial verification failed. "
            "Failure information will be supplied to the agent."
        )

    return {
        **state,
        "test_output": _trim(
            test_output,
            MAX_TEST_OUTPUT,
        ),
        "test_passed": bool(
            test_result.get("success")
        ),
        "error": None
        if test_result.get("success")
        else test_output,
        "files_changed": [],
        "repair_attempts": 0,
        "finished": False,
    }


graph_builder = StateGraph(AgentState)

graph_builder.add_node(
    "prepare_context",
    _prepare_context,
)

graph_builder.add_node(
    "repair",
    _repair,
)

graph_builder.add_node(
    "verify",
    _verify,
)

graph_builder.add_edge(
    START,
    "prepare_context",
)

graph_builder.add_edge(
    "prepare_context",
    "repair",
)

graph_builder.add_edge(
    "repair",
    "verify",
)

graph_builder.add_conditional_edges(
    "verify",
    _route_after_verification,
    {
        "repair": "repair",
        "done": END,
    },
)

graph = graph_builder.compile()

