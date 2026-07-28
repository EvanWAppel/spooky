"""The pipeline driver: ``uv run python -m build`` (TASKS D-15; PRD §8).

Run order lives HERE, not in filenames — modules were renamed from
``01_spine.py``-style because digit-prefixed modules cannot be imported by
tests. Steps not yet implemented fail loudly with their task id; nothing is
silently skipped.
"""

from __future__ import annotations

import argparse
import importlib
import logging

log = logging.getLogger(__name__)

# (step, implementing task) in strict run order.
STEPS: list[tuple[str, str]] = [
    ("spine", "D-01"),
    ("wikipedia", "D-07"),
    ("wikidata", "D-08"),
    ("labels", "D-09"),
    ("people", "D-11"),
    ("articles", "D-13"),
    ("merge", "E-03"),
    ("loglines", "F-02"),
    ("emit", "E-08"),
]


def run_step(name: str) -> None:
    task = dict(STEPS)[name]
    try:
        module = importlib.import_module(f"build.{name}")
    except ModuleNotFoundError as error:
        raise SystemExit(
            f"step {name!r} is not implemented yet (TASKS {task})"
        ) from error
    log.info("=== step: %s ===", name)
    module.main()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m build",
        description="Run the offline data pipeline in order: "
        + " -> ".join(name for name, _ in STEPS),
    )
    parser.add_argument(
        "--only",
        choices=[name for name, _ in STEPS],
        help="run a single step instead of the full pipeline",
    )
    arguments = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if arguments.only:
        run_step(arguments.only)
        return
    for name, _task in STEPS:
        run_step(name)


if __name__ == "__main__":
    main()
