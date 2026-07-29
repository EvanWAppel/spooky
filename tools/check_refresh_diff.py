"""Fail loudly if a data refresh would change human-reviewed content (I-05).

`build/merge.py` already refuses to overwrite the human layer. This is the
belt-and-braces check the scheduled refresh runs afterwards: it compares
every changed record against its committed version and exits non-zero if
any human-owned field moved on a record marked ``human-reviewed``.

    uv run python tools/check_refresh_diff.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HUMAN_OWNED_FIELDS = ("logline", "review_status", "reviewed_at", "review_note")
DATA_DIR = "data/episodes"


def changed_paths(data_dir: str = DATA_DIR) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", data_dir],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.split("\n") if line.strip()]


def committed_version(path: str) -> dict | None:
    """The record as committed, or None when the file is newly added."""
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def violations(paths: list[str]) -> list[str]:
    """Human-owned fields that changed on a human-reviewed record."""
    found = []
    for path in paths:
        before = committed_version(path)
        if before is None or before.get("review_status") != "human-reviewed":
            continue
        after = json.loads(Path(path).read_text())
        for field in HUMAN_OWNED_FIELDS:
            if before.get(field) != after.get(field):
                found.append(
                    f"{path}: {field}\n"
                    f"    committed: {before.get(field)!r}\n"
                    f"    refreshed: {after.get(field)!r}"
                )
    return found


def main() -> None:
    paths = changed_paths()
    if not paths:
        print("No record changes in this refresh.")
        return
    print(f"{len(paths)} record(s) changed by the refresh.")
    found = violations(paths)
    if found:
        print("\nRefresh would modify human-reviewed content:")
        for violation in found:
            print(f"  {violation}")
        sys.exit(1)
    print("No human-reviewed content changed.")


if __name__ == "__main__":
    main()
