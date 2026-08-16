"""Step 8 — AI-drafted loglines (TASKS F-01, F-02; PRD §F5).

Drafts one ≤30-word original logline per record via the Anthropic API, from
**factual inputs only**: title, credits, air date, classification, and the
episode's Wikipedia Production/Themes sections (CC BY-SA — permitted input;
C4 bars Fandom/TV Tropes/IMDb, none of which are touched).

Rules enforced mechanically, not by hope:

- ≤30 words, or the draft is rejected and re-requested (CLAUDE.md C3).
- No verbatim run of more than 8 consecutive words from any source text.
- Writes ``logline_generated`` and ``review_status: "ai-drafted"`` only.
  **Never writes ``logline``**, and never touches a human-reviewed record —
  it is skipped before any API call is made (F-06).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from build._usage import UsageAccumulator

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
WORD_CAP = 30
MAX_VERBATIM_RUN = 8
SOURCE_EXCERPT_CHARS = 1600

SYSTEM_PROMPT = f"""You write loglines for an X-Files episode data explorer.

A logline is a one-sentence teaser, {WORD_CAP} words or fewer — the premise,
not a plot recap and never the ending. Rules, all hard:
- {WORD_CAP} words maximum. Count them.
- Entirely your own wording. Do not reuse phrasing from the source notes.
- Present tense. No episode title in the text. No quotation marks.
- Ground yourself in the factual inputs and your own knowledge of the
  episode; if you are not certain of a plot detail, stay general rather
  than guessing.
Reply with the logline text alone — no preamble, no commentary."""


class LoglineError(RuntimeError):
    """A record's draft could not be produced within the rules."""


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def contains_verbatim_run(
    draft: str, sources: list[str], run: int = MAX_VERBATIM_RUN
) -> bool:
    """True if the draft shares a run of more than ``run`` words with a source."""
    draft_words = _words(draft)
    needles = {
        tuple(draft_words[i : i + run + 1]) for i in range(max(0, len(draft_words) - run))
    }
    for source in sources:
        source_words = _words(source)
        for i in range(max(0, len(source_words) - run)):
            if tuple(source_words[i : i + run + 1]) in needles:
                return True
    return False


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
        ]
    )


def draft_logline(
    client: Any,
    record: dict[str, Any],
    *,
    sources: list[str],
    retries: int = 3,
    usage: UsageAccumulator | None = None,
) -> str:
    """One validated draft; raises LoglineError when the rules can't be met."""
    prompt = _facts(record)
    if sources:
        excerpts = "\n\n".join(s[:SOURCE_EXCERPT_CHARS] for s in sources)
        prompt += (
            "\n\nBackground notes (context only — do NOT reuse their "
            f"wording):\n{excerpts}"
        )

    feedback = ""
    for attempt in range(retries):
        start = time.monotonic()
        response = client.messages.create(
            model=MODEL,
            # Generous: the model thinks before it answers, and a budget the
            # thinking exhausts truncates the reply before any text block.
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt + feedback}],
        )
        elapsed = time.monotonic() - start
        # The model may emit a thinking block before the text block —
        # take the first block that actually carries text.
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
        if usage is not None:
            usage.record(response, latency=elapsed, attempts=attempt + 1)
        return draft
    raise LoglineError(
        f"{record.get('id')}: no rule-compliant draft after {retries} attempts"
    )


def generate_all(
    client: Any, episodes_dir: Path, sections: dict[str, dict[str, Any]]
) -> int:
    """Draft every non-human-reviewed record in place; returns drafts written."""
    written = 0
    usage = UsageAccumulator(model=MODEL)
    paths = sorted(episodes_dir.glob("*.json"))
    for index, path in enumerate(paths, start=1):
        record = json.loads(path.read_text())
        if record.get("review_status") == "human-reviewed":
            log.info("skip %s: human-reviewed", record.get("id"))
            continue
        article = sections.get(record.get("enwiki_title") or "", {})
        sources = [
            text for text in (article.get("production"), article.get("themes")) if text
        ]
        draft = draft_logline(client, record, sources=sources, usage=usage)
        record["logline_generated"] = draft
        record["review_status"] = "ai-drafted"
        path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
        written += 1
        log.info("[%d/%d] %s: %s", index, len(paths), record["id"], draft)
    usage.log_summary()
    return written


def main() -> None:
    import anthropic
    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY missing from the environment/.env")
    sections_path = Path("data/raw/article_sections.json")
    sections = json.loads(sections_path.read_text()) if sections_path.exists() else {}
    client = anthropic.Anthropic()
    written = generate_all(client, Path("data/episodes"), sections)
    log.info("drafted %d loglines", written)


if __name__ == "__main__":
    main()
