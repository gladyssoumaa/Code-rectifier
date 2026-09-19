from __future__ import annotations

from config import TARGET_PROJECT, validate_config
from monitor.watcher import start_watcher


def main() -> None:
    print("=" * 60)
    print("CODE RECTIFIER")
    print("AUTONOMOUS PROJECT WATCHER")
    print("=" * 60)

    try:
        validate_config()
    except ValueError as error:
        print(f"\nConfiguration error: {error}")
        return

    print(f"Watching project: {TARGET_PROJECT}")
    print()

    try:
        start_watcher()

    except KeyboardInterrupt:
        print("\nWatcher stopped by user.")

    except Exception as error:
        print("\nWatcher encountered an error:")
        print(error)


if __name__ == "__main__":
    main()

