"""Logline triage — a read-only pre-pass that speeds up review.

Every draft is already ≤30 words and free of verbatim source runs (the
generation step enforces that). What remains is judgment: is this logline
*accurate* and *good enough to ship*? Reading 219 of them cold is the slow
part. Triage grades each one so the owner spends attention where it counts:

    A  ship as-is   — accurate, specific, no notes
    B  minor nit    — a small awkwardness or a soft generic ending
    C  rewrite      — likely inaccurate, invents a detail, or too vague

The grade and a one-line critique are written to ``data/logline_triage.json``.
The review CLI reads that file, orders the queue worst-first, and shows the
critique inline. **Triage never writes an episode record** — the sacred
``human-reviewed`` layer is untouchable here; grading is only advice.

    uv run python tools/triage.py            # grade every pending draft
    uv run python tools/review.py            # then review, worst-first

The judgment is the model's own knowledge of the episode measured against
the factual inputs — no source text is scraped or reused (CLAUDE.md C4).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"
GRADES = {"A", "B", "C"}
EPISODES_DIR = Path(__file__).resolve().parent.parent / "data" / "episodes"
TRIAGE_PATH = Path(__file__).resolve().parent.parent / "data" / "logline_triage.json"

SYSTEM_PROMPT = """You are a copy editor triaging one-sentence loglines for an
X-Files episode data explorer. Each logline is meant to be an accurate,
specific teaser of the episode's premise — never the ending, never a guess.

Judge the draft against the factual inputs and your own knowledge of the
episode. Grade it:
  A — accurate and specific; ship it as written.
  B — a minor nit: slightly awkward, or a soft/generic ending like "uncover
      the truth" that could be sharper. Still basically usable.
  C — needs a rewrite: likely inaccurate, invents a detail not supported by
      the facts, confuses this episode with another, or is too vague to mean
      anything.

Reply with ONE line and nothing else, in the form:
  <GRADE>: <critique in 12 words or fewer>
For A, the critique may simply be "accurate and specific". Be concrete about
what is wrong for B and C so the reviewer knows what to fix."""


class TriageError(RuntimeError):
    """A verdict could not be parsed or produced."""


def parse_verdict(text: str) -> tuple[str, str]:
    """Split a model reply like ``B - generic ending`` into (grade, critique).

    The grade is the first A/B/C token; anything else raises rather than
    guessing (CLAUDE.md: do not hide errors)."""
    match = re.match(r"\s*([A-Za-z])\s*[:.\-–\)]?\s*(.*)", text.strip(), re.DOTALL)
    if match is None or match.group(1).upper() not in GRADES:
        raise TriageError(f"unparseable grade in verdict: {text!r}")
    return match.group(1).upper(), match.group(2).strip()


def _facts(record: dict[str, Any]) -> str:
    position = (
        f"Season {record['season']}, episode {record['episode']}"
        if record.get("season") is not None
        else "Feature film"
    )
    return "\n".join(
        [
            f"Title: {record['title']}",
            position,
            f"Aired: {record.get('air_date')}",
            f"Classification: {record.get('label_derived')}",
            f"Written by: {', '.join(record.get('writers') or [])}",
            f"Directed by: {', '.join(record.get('director') or [])}",
            f"Guest cast: {', '.join((record.get('guest_cast') or [])[:6])}",
            "",
            f"Draft logline to grade:\n{record.get('logline_generated')}",
        ]
    )


def grade_record(
    client: Any, record: dict[str, Any], *, retries: int = 3
) -> dict[str, str]:
    """One graded verdict for a record. Raises if the draft is missing."""
    if not record.get("logline_generated"):
        raise TriageError(f"{record.get('id')}: no draft to grade")
    # Generous budget: the model may emit a thinking block first, and a budget
    # the thinking exhausts truncates the reply before any text block appears
    # (the same failure loglines.py guards against).
    for _attempt in range(retries):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _facts(record)}],
        )
        # A refusal is deterministic (e.g. an opaque base64 episode title trips
        # the safety classifier). Retrying only burns calls — fail fast and say
        # so, so it is never mistaken for a token-budget truncation.
        if getattr(response, "stop_reason", None) == "refusal":
            raise TriageError(
                f"{record.get('id')}: model refused to grade this draft — "
                "review it by hand"
            )
        text_block = next(
            (block.text for block in response.content if getattr(block, "text", None)),
            None,
        )
        if text_block is None:
            log.warning("%s: response had no text block; retrying", record.get("id"))
            continue
        grade, critique = parse_verdict(text_block)
        return {"id": record["id"], "grade": grade, "critique": critique}
    raise TriageError(
        f"{record.get('id')}: no gradeable response after {retries} attempts"
    )


def load_triage(path: Path) -> dict[str, dict[str, str]]:
    """The grade map, keyed by record id; empty if the file does not exist."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def grade_all(client: Any, episodes_dir: Path, out_path: Path) -> list[str]:
    """Grade every not-human-reviewed draft; merge into ``out_path`` in place.

    Never opens an episode file for writing — this pass is advice, not a
    review. The triage file is flushed after **every** record, so a crash or
    an ungradeable record can never discard the grades already earned (the
    first full run lost 214 that way). A record the model won't grade after
    its retries is logged loudly and skipped rather than aborting the batch —
    it simply gets no grade and sorts last in the review queue. Returns the
    list of ids that could not be graded."""
    triage = load_triage(out_path)
    failures: list[str] = []
    paths = sorted(episodes_dir.glob("*.json"))
    for index, path in enumerate(paths, start=1):
        record = json.loads(path.read_text())
        if record.get("review_status") == "human-reviewed":
            continue
        try:
            verdict = grade_record(client, record)
        except TriageError as error:
            log.error("triage failed for %s: %s", record.get("id"), error)
            failures.append(record["id"])
            continue
        triage[record["id"]] = {
            "grade": verdict["grade"],
            "critique": verdict["critique"],
        }
        out_path.write_text(json.dumps(triage, indent=1, ensure_ascii=False) + "\n")
        log.info(
            "[%d/%d] %s: %s — %s",
            index,
            len(paths),
            record["id"],
            verdict["grade"],
            verdict["critique"],
        )
    if failures:
        log.error(
            "%d records could not be graded: %s", len(failures), ", ".join(failures)
        )
    return failures


def _summary(triage: dict[str, dict[str, str]]) -> str:
    counts = {grade: 0 for grade in sorted(GRADES)}
    for verdict in triage.values():
        counts[verdict["grade"]] = counts.get(verdict["grade"], 0) + 1
    return "  ".join(f"{grade}={counts[grade]}" for grade in sorted(GRADES))


def main() -> None:
    import anthropic
    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY missing from the environment/.env")
    client = anthropic.Anthropic()
    failures = grade_all(client, EPISODES_DIR, TRIAGE_PATH)
    triage = load_triage(TRIAGE_PATH)
    log.info("graded %d drafts → %s", len(triage), _summary(triage))
    if failures:
        raise SystemExit(
            f"{len(failures)} records could not be graded: {', '.join(failures)}. "
            "Their grades are absent; they sort last in review. Re-run to retry."
        )


if __name__ == "__main__":
    main()
