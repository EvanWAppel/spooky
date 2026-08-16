"""Corrective rewrite pass for AI-drafted loglines (Group F follow-up).

The first pass (``build/loglines.py``) drafts one logline per record; the
triage pass (``tools/triage.py``) grades each draft A/B/C with a one-line
critique. This step closes the loop: it hands the model its own draft **plus
that critique as an editor's note** and asks for a corrected logline. The C's
in particular carry factual errors triage already diagnosed — a missile silo
mistaken for a UN bunker, a kidnapping invented — and the critique states the
correct fact, so the rewrite can fix it.

Nothing about the ownership model changes. The output is still a machine draft
awaiting the owner's review:

- Same hard rules as the first draft — ≤30 words, no verbatim run of more than
  8 words from any source (reused from ``build.loglines``).
- Writes ``logline_generated`` only; ``review_status`` stays ``ai-drafted``.
  **Never writes ``logline``**, and a ``human-reviewed`` record is skipped
  before any API call — its content is sacred (CLAUDE.md).
- Grounded only in factual inputs, the model's own knowledge, and the triage
  critique (the triage model's judgement, not scraped source text — C4 holds).

    uv run python -m build.rewrite      # revise every pending draft, worst first
    uv run python tools/triage.py       # then re-grade to confirm improvement
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Allow `uv run python build/rewrite.py` as well as `-m build.rewrite`: run as a
# bare script, Python puts build/ on sys.path instead of the repo root, so the
# `build`/`tools` packages are unimportable. Put the repo root first.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build.loglines import (  # noqa: E402  (after the path bootstrap above)
    MODEL,
    SOURCE_EXCERPT_CHARS,
    WORD_CAP,
    LoglineError,
    _facts,
    contains_verbatim_run,
)

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are revising a one-sentence logline for an X-Files
episode data explorer, guided by an editor's note that flags what is wrong.

A logline is a teaser of the premise, {WORD_CAP} words or fewer — never the
ending, never a guessed detail. Rules, all hard:
- {WORD_CAP} words maximum. Count them.
- Entirely your own wording. Do not reuse phrasing from the source notes.
- Present tense. No episode title in the text. No quotation marks.
- Fix exactly what the editor's note identifies. If the note says the draft is
  already accurate and specific, return it unchanged or only lightly tightened
  — do not rewrite for its own sake.
- Ground yourself in the factual inputs and your own knowledge of the episode;
  if you are unsure of a detail, stay general rather than guessing.
Reply with the logline text alone — no preamble, no commentary."""


def rewrite_logline(
    client: Any,
    record: dict[str, Any],
    *,
    sources: list[str],
    critique: str,
    retries: int = 3,
) -> str:
    """One validated rewrite; raises LoglineError when the rules can't be met."""
    prompt = _facts(record)
    prompt += f"\n\nCurrent draft:\n{record.get('logline_generated')}"
    prompt += f"\n\nEditor's note:\n{critique}" if critique else ""
    if sources:
        excerpts = "\n\n".join(s[:SOURCE_EXCERPT_CHARS] for s in sources)
        prompt += (
            "\n\nBackground notes (context only — do NOT reuse their "
            f"wording):\n{excerpts}"
        )

    feedback = ""
    for _attempt in range(retries):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt + feedback}],
        )
        # A refusal is deterministic (e.g. the base64 episode title s11e07,
        # "Rm9sbG93ZXJz", trips the safety classifier). Retrying only burns
        # calls — fail fast so it is never mistaken for a token-budget
        # truncation (the same guard triage.py carries).
        if getattr(response, "stop_reason", None) == "refusal":
            raise LoglineError(
                f"{record.get('id')}: model refused to rewrite this draft — "
                "review it by hand"
            )
        text_block = next(
            (block.text for block in response.content if getattr(block, "text", None)),
            None,
        )
        if text_block is None:
            log.warning("%s: response had no text block; retrying", record.get("id"))
            feedback = "\n\nReply with the logline text alone."
            continue
        draft = text_block.strip().strip('"')
        if len(draft.split()) > WORD_CAP:
            feedback = (
                f"\n\nYour previous attempt was {len(draft.split())} words — "
                f"too long. {WORD_CAP} words maximum."
            )
            continue
        if contains_verbatim_run(draft, sources):
            feedback = (
                "\n\nYour previous attempt reused wording from the background "
                "notes. Rephrase entirely in your own words."
            )
            continue
        return draft
    raise LoglineError(
        f"{record.get('id')}: no rule-compliant rewrite after {retries} attempts"
    )


def rewrite_all(
    client: Any,
    episodes_dir: Path,
    sections: dict[str, dict[str, Any]],
    triage: dict[str, dict[str, str]],
) -> tuple[int, list[str]]:
    """Revise every not-human-reviewed draft in place.

    Returns ``(written, failures)`` — the count of drafts improved and the ids
    that could not be rewritten. A record with no existing draft is skipped
    (nothing to correct); a human-reviewed record is skipped before any API
    call (its content is sacred). The critique comes from ``triage``; a record
    with no grade is still rewritten, just without an editor's note to steer it.

    A record the model won't rewrite (a deterministic refusal, or three failed
    attempts) is logged loudly and skipped rather than aborting the batch — it
    keeps its existing draft, which the owner then reviews by hand. The caller
    surfaces the failures with a non-zero exit; nothing is swallowed silently."""
    written = 0
    failures: list[str] = []
    paths = sorted(episodes_dir.glob("*.json"))
    for index, path in enumerate(paths, start=1):
        record = json.loads(path.read_text())
        if record.get("review_status") == "human-reviewed":
            log.info("skip %s: human-reviewed", record.get("id"))
            continue
        if not record.get("logline_generated"):
            log.info("skip %s: no draft to rewrite", record.get("id"))
            continue
        critique = triage.get(record["id"], {}).get("critique", "")
        article = sections.get(record.get("enwiki_title") or "", {})
        sources = [
            text for text in (article.get("production"), article.get("themes")) if text
        ]
        try:
            revised = rewrite_logline(client, record, sources=sources, critique=critique)
        except LoglineError as error:
            log.error("rewrite failed for %s: %s", record.get("id"), error)
            failures.append(record["id"])
            continue
        record["logline_generated"] = revised
        record["review_status"] = "ai-drafted"
        path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
        written += 1
        log.info("[%d/%d] %s: %s", index, len(paths), record["id"], revised)
    return written, failures


def main() -> None:
    import anthropic
    from dotenv import load_dotenv

    from tools.triage import TRIAGE_PATH, load_triage

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY missing from the environment/.env")
    sections_path = Path("data/raw/article_sections.json")
    sections = json.loads(sections_path.read_text()) if sections_path.exists() else {}
    triage = load_triage(TRIAGE_PATH)
    client = anthropic.Anthropic()
    written, failures = rewrite_all(client, Path("data/episodes"), sections, triage)
    log.info("rewrote %d loglines", written)
    if failures:
        raise SystemExit(
            f"{len(failures)} records could not be rewritten: "
            f"{', '.join(failures)}. They keep their prior draft — review by "
            "hand. Re-run to retry."
        )


if __name__ == "__main__":
    main()
