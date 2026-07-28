"""Brace-balanced wikitext parsing for Wikipedia episode tables (TASKS D-04–D-06).

PRD §8.1 landmines this module exists to defuse:

- **Not a regex.** Episode rows nest templates (``{{Start date|…}}``,
  ``{{StoryTeleplay|…}}``, ``{{cite episode |…}}``) and a non-greedy regex
  stops at the first ``}}`` — silently dropping all 16 season 10–11 rows.
- Param splitting must also be depth-aware: pipes inside nested ``{{…}}`` and
  ``[[target|display]]`` links are not parameter separators.
- The mythology dagger is matched case-insensitively (``{{Double-dagger}}`` in
  season 3, ``{{double dagger}}`` in the revival) on the ``RTitle`` param
  only — each season page also has a prose legend line that must not count.
"""

from __future__ import annotations

import re

# Season 1 uses the literal ‡ character; later seasons use the template.
_DAGGER = re.compile(r"double[- ]dagger|‡", re.IGNORECASE)
_HR = re.compile(r"<hr\s*/?>", re.IGNORECASE)
_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.DOTALL)


def extract_templates(wikitext: str, prefix: str = "Episode list") -> list[str]:
    """Return every complete ``{{<prefix>…}}`` block, brace-balanced."""
    blocks: list[str] = []
    i = 0
    while True:
        start = wikitext.find("{{", i)
        if start == -1:
            return blocks
        name = wikitext[start + 2 : start + 2 + len(prefix)]
        if name.lower() != prefix.lower():
            i = start + 2
            continue
        depth = 0
        j = start
        while j < len(wikitext):
            if wikitext.startswith("{{", j):
                depth += 1
                j += 2
            elif wikitext.startswith("}}", j):
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        blocks.append(wikitext[start:j])
        i = j


def _split_top_level(body: str) -> list[str]:
    """Split on ``|`` only at depth 0 of both ``{{…}}`` and ``[[…]]``."""
    parts: list[str] = []
    buf: list[str] = []
    braces = 0
    brackets = 0
    i = 0
    while i < len(body):
        pair = body[i : i + 2]
        if pair == "{{":
            braces += 1
        elif pair == "}}":
            braces -= 1
        elif pair == "[[":
            brackets += 1
        elif pair == "]]":
            brackets -= 1
        else:
            char = body[i]
            if char == "|" and braces == 0 and brackets == 0:
                parts.append("".join(buf))
                buf = []
            else:
                buf.append(char)
            i += 1
            continue
        buf.append(pair)
        i += 2
    parts.append("".join(buf))
    return parts


def parse_template_params(template: str) -> dict[str, str]:
    """Named params of one ``{{…}}`` block. Positional params are ignored."""
    inner = template.strip()
    if inner.startswith("{{") and inner.endswith("}}"):
        inner = inner[2:-2]
    params: dict[str, str] = {}
    for part in _split_top_level(inner)[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        params[key.strip()] = value.strip()
    return params


def extract_episode_rows(wikitext: str) -> list[dict[str, str]]:
    """Every episode row on a season page, as parsed named params."""
    rows = [parse_template_params(block) for block in extract_templates(wikitext)]
    return [row for row in rows if "EpisodeNumber" in row]


def is_mythology_flagged(row: dict[str, str]) -> bool:
    """True when the row's ``RTitle`` carries the mythology dagger."""
    return bool(_DAGGER.search(row.get("RTitle", "")))


def strip_refs(value: str) -> str:
    """Drop ``<ref>…</ref>`` / ``<ref …/>`` citation markup from a value."""
    return _REF.sub("", value).strip()


def split_multi_value(value: str) -> list[str]:
    """Split an ``<hr>``-joined multi-value field into its parts."""
    return [part.strip() for part in _HR.split(value) if part.strip()]


def parse_wikilinks(value: str) -> list[str]:
    """Display names of every ``[[…]]`` link; a bare string is itself."""
    links = _WIKILINK.findall(value)
    if links:
        return [(display or target).strip() for target, display in links]
    stripped = value.strip()
    return [stripped] if stripped else []
