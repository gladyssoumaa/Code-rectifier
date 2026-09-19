
from __future__ import annotations

import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import (
    TARGET_PROJECT,
    TEST_COMMAND,
    TASK,
    WATCH_INTERVAL,
    DEBOUNCE_SECONDS,
    IGNORED_DIRECTORIES,
    IGNORED_FILES,
)

from tools import executor, git
from agent.graph import graph


class ProjectWatcher(FileSystemEventHandler):

    def __init__(self):
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._agent_running = False
        self._stop_requested = False

    def on_created(self, event):
        self._handle(event)

    def on_modified(self, event):
        self._handle(event)

    def on_deleted(self, event):
        self._handle(event)

    def on_moved(self, event):
        self._handle(event)

    def _is_relevant(
        self,
        path_str: str,
    ) -> bool:
        path = Path(path_str)

        if any(
            part in IGNORED_DIRECTORIES
            for part in path.parts
        ):
            return False

        if path.name in IGNORED_FILES:
            return False

        return True

    def _handle(self, event):
        if event.is_directory:
            return

        if not self._is_relevant(
            event.src_path
        ):
            return

        print(
            f"[CHANGE] {event.src_path}"
        )

        self._schedule_check()

    def _schedule_check(self):
        with self._lock:
            if self._stop_requested:
                return

            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(
                DEBOUNCE_SECONDS,
                self._on_settled,
            )

            self._timer.daemon = True
            self._timer.start()

    def _on_settled(self):
        with self._lock:
            if self._stop_requested:
                return

            if self._agent_running:
                print(
                    "[Watcher] Agent already running."
                )
                return

        print(
            "[Watcher] Changes settled. "
            "Checking tests..."
        )

        if self._tests_currently_failing():
            print(
                "[Watcher] Failure detected. "
                "Starting Code Rectifier..."
            )

            self._run_agent()

        else:
            print(
                "[Watcher] Tests are passing. "
                "No action needed."
            )

    def _tests_currently_failing(self) -> bool:
        result = executor.run_command(
            TEST_COMMAND
        )

        output = (
            result.get("stdout", "")
            + "\n"
            + result.get("stderr", "")
        ).strip()

        if output:
            print(output)

        return not result.get(
            "success",
            False,
        )

    def _run_agent(self):
        with self._lock:
            if self._agent_running:
                return

            self._agent_running = True

        snapshot_hash = None

        try:
            repository = git.is_repository()

            if repository:
                status_before = git.status()

                if not status_before.get(
                    "success",
                    False,
                ):
                    print(
                        "[Watcher] Unable to read Git status."
                    )
                else:
                    if status_before.get(
                        "stdout",
                        "",
                    ).strip():
                        print(
                            "[Watcher] Existing uncommitted "
                            "changes detected."
                        )

                commit_result = git.commit(
                    "code-rectifier: pre-fix snapshot"
                )

                if commit_result.get(
                    "success",
                    False,
                ):
                    head = git.head_commit()

                    if head.get(
                        "success",
                        False,
                    ):
                        snapshot_hash = (
                            head.get(
                                "stdout",
                                "",
                            ).strip()
                        )

                else:
                    print(
                        "[Watcher] Git snapshot was not created."
                    )

            initial_state = {
                "task": TASK,
                "project_path": str(
                    TARGET_PROJECT
                ),
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

            final_state = graph.invoke(
                initial_state
            )

            final_test = executor.run_command(
                TEST_COMMAND
            )

            tests_passed = bool(
                final_test.get(
                    "success",
                    False,
                )
            )

            if tests_passed:
                print(
                    "[Watcher] Code Rectifier "
                    "successfully fixed the project."
                )

            else:
                print(
                    "[Watcher] Code Rectifier did not "
                    "produce a passing project."
                )

                output = final_state.get(
                    "output",
                    "",
                )

                if output:
                    print(output)

                if snapshot_hash:
                    print(
                        "[Watcher] Reverting to "
                        f"{snapshot_hash[:8]}..."
                    )

                    revert_result = git.revert_to(
                        snapshot_hash
                    )

                    if not revert_result.get(
                        "success",
                        False,
                    ):
                        print(
                            "[Watcher] Git rollback failed:"
                        )
                        print(
                            revert_result.get(
                                "stderr",
                                "",
                            )
                        )

        except KeyboardInterrupt:
            print(
                "[Watcher] Agent interrupted."
            )

        except Exception as error:
            print(
                "[Watcher] Agent execution failed:"
            )
            print(error)

            if snapshot_hash:
                print(
                    "[Watcher] Attempting rollback..."
                )

                git.revert_to(
                    snapshot_hash
                )

        finally:
            with self._lock:
                self._agent_running = False

    def stop(self):
        with self._lock:
            self._stop_requested = True

            if self._timer is not None:
                self._timer.cancel()

                self._timer = None


def start_watcher():
    event_handler = ProjectWatcher()

    observer = Observer()

    observer.schedule(
        event_handler,
        str(TARGET_PROJECT),
        recursive=True,
    )

    observer.start()

    print(
        f"Watching project: {TARGET_PROJECT}"
    )

    try:
        while True:
            time.sleep(WATCH_INTERVAL)

    except KeyboardInterrupt:
        print(
            "\nStopping Code Rectifier watcher..."
        )

    finally:
        event_handler.stop()
        observer.stop()
        observer.join()


if __name__ == "__main__":
    start_watcher()

