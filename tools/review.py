"""The logline review CLI (TASKS F-03, F-04, F-05).

The only path by which machine-drafted prose becomes human-owned. Walks
every record that is not yet ``human-reviewed``, shows the draft alongside
the episode's facts, and takes one of:

    a  approve — copy the draft into ``logline``, mark human-reviewed
    e  edit    — store your own wording instead
    r  reject  — mark needs-work with a note, leave it pending
    s  skip    — move on, decide later
    q  quit    — stop; everything already decided is saved

    uv run python tools/review.py
    uv run python tools/review.py --status
    uv run python tools/review.py --season 5

Writes ``data/episodes/*.json`` in place. Once a record is human-reviewed,
no pipeline step may overwrite it (CLAUDE.md; build/merge.py guards it).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WORD_CAP = 30
EPISODES_DIR = Path(__file__).resolve().parent.parent / "data" / "episodes"

# ANSI — the terminal equivalent of the site's palette.
_DIM = "\033[2m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_AMBER = "\033[33m"
_CYAN = "\033[36m"
_RESET = "\033[0m"


class ReviewError(RuntimeError):
    """A review action could not be applied."""


def load_records(episodes_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in sorted(episodes_dir.glob("*.json"))]


def pending(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Records still awaiting the owner's verdict, in air order."""
    return [r for r in records if r.get("review_status") != "human-reviewed"]


def status_line(records: list[dict[str, Any]]) -> str:
    reviewed = sum(1 for r in records if r.get("review_status") == "human-reviewed")
    return f"{reviewed} / {len(records)} human-reviewed"


def _load_one(episodes_dir: Path, record_id: str) -> tuple[Path, dict[str, Any]]:
    path = episodes_dir / f"{record_id}.json"
    if not path.exists():
        raise ReviewError(f"no record {record_id!r} in {episodes_dir}")
    return path, json.loads(path.read_text())


def _write(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def approve(episodes_dir: Path, record_id: str, *, now: str | None = None) -> None:
    """Promote the machine draft to the owner's logline verbatim."""
    path, record = _load_one(episodes_dir, record_id)
    draft = record.get("logline_generated")
    if not draft:
        raise ReviewError(f"{record_id}: no draft to approve")
    record["logline"] = draft
    record["review_status"] = "human-reviewed"
    record["reviewed_at"] = now or _now()
    record["review_note"] = None
    _write(path, record)


def edit(
    episodes_dir: Path, record_id: str, text: str, *, now: str | None = None
) -> None:
    """Store the owner's own wording; the 30-word cap binds here too (C3)."""
    cleaned = text.strip()
    if not cleaned:
        raise ReviewError(f"{record_id}: logline is empty")
    if len(cleaned.split()) > WORD_CAP:
        raise ReviewError(
            f"{record_id}: {len(cleaned.split())} words — the cap is {WORD_CAP} words"
        )
    path, record = _load_one(episodes_dir, record_id)
    record["logline"] = cleaned
    record["review_status"] = "human-reviewed"
    record["reviewed_at"] = now or _now()
    record["review_note"] = None
    _write(path, record)


def reject(episodes_dir: Path, record_id: str, note: str) -> None:
    """Send the draft back with a note; the record stays pending."""
    path, record = _load_one(episodes_dir, record_id)
    record["review_status"] = "needs-work"
    record["review_note"] = note.strip() or None
    _write(path, record)


def _render(record: dict[str, Any], position: str) -> str:
    where = (
        f"S{int(record['season']):02d}E{int(record['episode']):02d}"
        if record.get("season") is not None
        else "Film"
    )
    contested = f"  {_AMBER}contested{_RESET}" if record.get("label_contested") else ""
    people = ", ".join(record.get("writers") or []) or "unknown"
    lines = [
        "",
        f"{_DIM}{position}{_RESET}",
        f"{_BOLD}{record['title']}{_RESET}  {_DIM}{where}"
        f" · {record.get('air_date')} · {record.get('label_derived')}{_RESET}{contested}",
        f"{_DIM}written by {people}{_RESET}",
        "",
        f"  {_CYAN}{record.get('logline_generated') or '(no draft)'}{_RESET}",
        "",
    ]
    if record.get("review_note"):
        lines.append(f"  {_AMBER}previous note: {record['review_note']}{_RESET}\n")
    return "\n".join(lines)


def run_interactive(episodes_dir: Path, season: int | None = None) -> None:
    records = load_records(episodes_dir)
    queue = pending(records)
    if season is not None:
        queue = [r for r in queue if r.get("season") == season]
    if not queue:
        print(f"Nothing pending. {status_line(load_records(episodes_dir))}")
        return

    print(f"{_BOLD}spooky logline review{_RESET}")
    print(f"{status_line(records)} · {len(queue)} in this queue")
    print(f"{_DIM}[a]pprove  [e]dit  [r]eject  [s]kip  [q]uit{_RESET}")

    for index, record in enumerate(queue, start=1):
        record_id = record["id"]
        print(_render(record, f"{index}/{len(queue)}"))
        while True:
            choice = input("  > ").strip().lower()
            if choice in ("a", ""):
                approve(episodes_dir, record_id)
                print(f"  {_GREEN}approved{_RESET}")
                break
            if choice == "e":
                text = input("  new logline: ")
                try:
                    edit(episodes_dir, record_id, text)
                except ReviewError as error:
                    print(f"  {_AMBER}{error}{_RESET}")
                    continue
                print(f"  {_GREEN}saved{_RESET}")
                break
            if choice == "r":
                reject(episodes_dir, record_id, input("  what's wrong: "))
                print(f"  {_AMBER}marked needs-work{_RESET}")
                break
            if choice == "s":
                break
            if choice == "q":
                print(f"\n{status_line(load_records(episodes_dir))}")
                return
            print(f"  {_DIM}a / e / r / s / q{_RESET}")

    print(f"\n{status_line(load_records(episodes_dir))}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Review AI-drafted loglines.")
    parser.add_argument(
        "--status", action="store_true", help="print review progress and exit"
    )
    parser.add_argument("--season", type=int, help="review only this season's records")
    parser.add_argument(
        "--dir", type=Path, default=EPISODES_DIR, help="records directory"
    )
    arguments = parser.parse_args()

    if arguments.status:
        records = load_records(arguments.dir)
        print(status_line(records))
        remaining = pending(records)
        if remaining:
            needs_work = [r for r in remaining if r["review_status"] == "needs-work"]
            print(f"{len(remaining)} pending ({len(needs_work)} marked needs-work)")
        return

    run_interactive(arguments.dir, arguments.season)


if __name__ == "__main__":
    main()
