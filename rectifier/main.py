from __future__ import annotations

from agent.graph import graph
from config import TARGET_PROJECT, validate_config


def create_initial_state(task: str) -> dict:
    return {
        "task": task,
        "project_path": str(TARGET_PROJECT),
        "plan": [],
        "current_step": 0,
        "repair_attempts": 0,
        "files_changed": [],
        "message": [],
        "output": "",
        "error": None,
        "test_output": "",
        "test_passed": False,
        "finished": False,
    }


def main() -> None:
    print("=" * 60)
    print("CODE RECTIFIER")
    print("AUTONOMOUS CODING AGENT")
    print("=" * 60)

    try:
        validate_config()
    except ValueError as error:
        print(f"\nConfiguration error: {error}")
        return

    print(f"Project: {TARGET_PROJECT}")
    print()

    task = input(
        "What would you like me to implement or fix?\n> "
    ).strip()

    if not task:
        print("No task provided.")
        return

    initial_state = create_initial_state(task)

    print("\nStarting Code Rectifier...\n")

    try:
        result = graph.invoke(initial_state)

    except KeyboardInterrupt:
        print("\nAgent interrupted by user.")
        return

    except Exception as error:
        print(
            "\nCode Rectifier encountered an error:"
        )
        print(error)
        return

    print("\n" + "=" * 60)

    if result.get("test_passed"):
        print("AGENT RESULT: PASS")
    else:
        print("AGENT RESULT: FAIL")

    print("=" * 60)

    output = result.get("output", "")

    if output:
        print("\nAgent output:")
        print(output)

    test_output = result.get("test_output", "")

    if test_output:
        print("\nFinal test result:")
        print(test_output)

    error = result.get("error")

    if error and not test_output:
        print("\nError:")
        print(error)

    print(
        f"\nRepair attempts: "
        f"{result.get('repair_attempts', 0)}"
    )

    files_changed = result.get(
        "files_changed",
        [],
    )

    if files_changed:
        print("\nFiles changed:")

        for file_path in files_changed:
            print(f"  - {file_path}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

