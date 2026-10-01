"""Server-rendered, crawlable content pages (Group R.3, decision D-30).

Dash renders client-side, so a crawler or a recruiter's Google result sees an
empty shell (PRD §4.1). These pages fix that without touching the app: plain
semantic HTML rendered from ``data/episodes/*.json``, one per episode and
season plus an index and a text provenance page, each at its own canonical URL
with meta/Open Graph tags, ``TVEpisode`` JSON-LD, the CC BY-SA footer, and a
link into the interactive app. A sitemap + robots.txt tie them together.

Legal posture identical to the app: plain text, original markup only, no
imagery, no synopses, no IMDb numbers (C1–C3). Flask serves these (see app.py).
"""

from __future__ import annotations

import json
import logging
from html import escape
from typing import Any

import pandas as pd

from spooky.links import imdb_url, tmdb_watch_url
from spooky.provenance import SOURCES, contested_breakdown, source_coverage
from spooky.search import displayed_logline
from spooky.values import as_int, is_missing

log = logging.getLogger(__name__)

BASE_URL = "https://spooky.evanappel.me"

# Minimal inline style so a human arriving from a search result sees a legible
# page, not raw HTML — kept inline so the pages carry no external dependency.
_STYLE = (
    "body{background:#111417;color:#f1f5f2;font:16px/1.6 system-ui,sans-serif;"
    "max-width:760px;margin:0 auto;padding:40px 16px}"
    "a{color:#8fc7ff}h1{font-weight:400;letter-spacing:-1px}"
    "h2{font-weight:400;margin-top:2em}dt{color:#9aa8a0}"
    "ul{padding-left:1.1em}footer{margin-top:3em;color:#9aa8a0;font-size:12px}"
)

_FOOTER = (
    "Episode metadata and ratings from TVmaze, licensed CC BY-SA 4.0. Additional "
    "episode data derived from Wikipedia, licensed CC BY-SA 4.0; modified. "
    "Identifier data from Wikidata (CC0). Mythology/monster-of-the-week labels "
    "adapted from dom111/xfiles-episode-picker (MIT). The derived dataset "
    "published here is licensed CC BY-SA 4.0. This is an unofficial fan project. "
    "It is not affiliated with, endorsed by, or approved by 20th Television, The "
    "Walt Disney Company, or Ten Thirteen Productions. The X-Files and all "
    "related marks are the property of their respective owners."
)


def _jsonld(data: dict) -> str:
    """Serialize JSON-LD safe to embed in a <script>: unicode-escape the
    characters that could otherwise break out of the tag (notably </script>)."""
    return (
        json.dumps(data)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _text(value: Any) -> str:
    """Escaped text for a record field, with a NaN-safe empty fallback.

    `record.get(key) or ""` is wrong here: a pandas NaN is truthy, so the
    fallback never fires and the literal 'nan' reaches the page (values.py).
    """
    return "" if is_missing(value) else escape(str(value))


def _seasons(df: pd.DataFrame) -> set[int]:
    """The distinct season numbers present (films, with no season, excluded)."""
    return {value for value in (as_int(s) for s in df["season"]) if value is not None}


def _date(value: Any) -> str:
    """ISO date string from a Timestamp or a plain string; '' when missing."""
    if is_missing(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return str(value)[:10]


def _page(title: str, description: str, canonical: str, body: str) -> str:
    """Wrap a body in a full HTML document with head metadata and the footer."""
    t, d = escape(title), escape(description)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{t} · spooky</title>\n"
        f'<meta name="description" content="{d}">\n'
        f'<link rel="canonical" href="{escape(canonical)}">\n'
        f'<meta property="og:title" content="{t}">\n'
        f'<meta property="og:description" content="{d}">\n'
        f'<meta property="og:url" content="{escape(canonical)}">\n'
        '<meta property="og:type" content="website">\n'
        f"<style>{_STYLE}</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        f"<footer><p>{escape(_FOOTER)}</p></footer>\n"
        "</body>\n</html>\n"
    )


def _credits(record: dict) -> str:
    parts = []
    for label, key in (("Director", "director"), ("Writers", "writers")):
        people = record.get(key) or []
        if isinstance(people, (list, tuple)) and len(people):
            names = ", ".join(escape(str(p)) for p in people)
            parts.append(f"<dt>{label}</dt><dd>{names}</dd>")
    cast = record.get("guest_cast") or []
    if isinstance(cast, (list, tuple)) and len(cast):
        names = ", ".join(escape(str(p)) for p in cast)
        parts.append(f"<dt>Guest cast</dt><dd>{names}</dd>")
    return f"<dl>{''.join(parts)}</dl>" if parts else ""


def _source_split(record: dict) -> str:
    """The per-source verdicts and rationale for a contested record."""
    rows = []
    for source in SOURCES:
        value = record.get(source.column)
        verdict = "no data" if is_missing(value) else str(value)
        rows.append(f"<li>{escape(source.label)}: {escape(verdict)}</li>")
    rationale = _text(record.get("label_rationale"))
    return (
        "<section><h2>Why it's contested</h2>"
        f"<ul>{''.join(rows)}</ul>"
        f"<p>{rationale}</p></section>"
    )


def _app_link(record: dict) -> str:
    """Canonical URL of this record inside the interactive app."""
    season = as_int(record.get("season"))
    if season is None:  # films have no season page
        return f"{BASE_URL}/"
    return f"{BASE_URL}/season/{season}?selected={record['id']}"


def render_episode(record: dict) -> str:
    title = str(record["title"])
    category = "" if is_missing(record.get("category")) else str(record["category"])
    logline = displayed_logline(record)
    air = _date(record.get("air_date"))
    canonical = f"{BASE_URL}/episode/{record['id']}"

    out = []
    imdb = imdb_url(record.get("imdb_id"))
    if imdb:
        out.append(f'<a href="{escape(imdb)}">IMDb</a>')
    tmdb = tmdb_watch_url(record.get("season"), record.get("tmdb_movie_id"))
    if tmdb:
        out.append(f'<a href="{escape(tmdb)}">Where to watch (TMDB)</a>')

    is_film = as_int(record.get("season")) is None
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Movie" if is_film else "TVEpisode",
        "name": title,
        "description": logline,
        "url": canonical,
    }
    if air:
        jsonld["datePublished"] = air
    if not is_film:
        jsonld["seasonNumber"] = as_int(record.get("season"))
        jsonld["episodeNumber"] = as_int(record.get("episode"))
        jsonld["partOfSeries"] = {"@type": "TVSeries", "name": "The X-Files"}

    body = (
        "<main>"
        f"<p>{_text(record.get('season_episode'))}</p>"
        f"<h1>{escape(title)}</h1>"
        f"<p>Classification: {escape(category)}</p>"
        + (f"<p>{escape(logline)}</p>" if logline else "")
        + (f"<p>First aired: {escape(air)}</p>" if air else "")
        + _credits(record)
        + (_source_split(record) if record.get("label_contested") else "")
        + (f"<p>{' · '.join(out)}</p>" if out else "")
        + f'<p><a href="{escape(_app_link(record))}">'
        + "Open in the interactive explorer</a></p>"
        + "</main>"
        + f'<script type="application/ld+json">{_jsonld(jsonld)}</script>'
    )
    description = logline or f"{title} — The X-Files, {category}."
    return _page(title, description, canonical, body)


def render_season(season: int, records: list[dict]) -> str:
    items = []
    for record in records:
        href = f"{BASE_URL}/episode/{escape(str(record['id']))}"
        se = _text(record.get("season_episode"))
        title = escape(str(record["title"]))
        category = _text(record.get("category"))
        items.append(f'<li><a href="{href}">{se} · {title}</a> — {category}</li>')
    body = (
        "<main>"
        f"<h1>The X-Files — Season {season}</h1>"
        f'<p><a href="{BASE_URL}/season/{season}">'
        "Open this season in the explorer</a></p>"
        f"<ul>{''.join(items)}</ul>"
        "</main>"
    )
    title = f"Season {season}"
    return _page(
        title,
        f"Every Season {season} episode of The X-Files.",
        f"{BASE_URL}/seasons/{season}",
        body,
    )


def render_index(df: pd.DataFrame) -> str:
    seasons = sorted(_seasons(df))
    season_links = "".join(
        f'<li><a href="{BASE_URL}/seasons/{s}">Season {s}</a></li>' for s in seasons
    )
    episode_items = "".join(
        f'<li><a href="{BASE_URL}/episode/{escape(str(record["id"]))}">'
        f"{_text(record.get('season_episode'))} · "
        f"{escape(str(record['title']))}</a> — "
        f"{_text(record.get('category'))}</li>"
        for record in df.sort_values("air_date").to_dict("records")
    )
    body = (
        "<main>"
        "<h1>spooky — an X-Files episode data explorer</h1>"
        "<p>Nobody agrees which episodes of The X-Files are “mythology” (the "
        "long-running conspiracy arc) versus monster-of-the-week. Three sources — "
        "Fox's Mythology DVDs, Wikipedia's dagger flags, and the dom111 fan "
        "dataset — give three different counts and disagree on roughly one episode "
        "in ten. This project stores all three verdicts per episode, derives a "
        "defensible label by vote, and shows the disagreement as a feature rather "
        "than hiding it.</p>"
        f'<p><a href="{BASE_URL}/">Open the interactive explorer</a> · '
        f'<a href="{BASE_URL}/provenance-text">How the data is sourced</a></p>'
        f"<h2>Seasons</h2><ul>{season_links}</ul>"
        f"<h2>All episodes</h2><ul>{episode_items}</ul>"
        "</main>"
    )
    return _page(
        "spooky — an X-Files episode data explorer",
        "Explore how The X-Files' balance of mythology vs monster-of-the-week "
        "episodes changed across eleven seasons.",
        f"{BASE_URL}/overview",
        body,
    )


def render_provenance(df: pd.DataFrame) -> str:
    coverage = "".join(
        f"<li>{escape(row['label'])}: covers {row['covers']}, abstains "
        f"{row['abstains']}, calls mythology {row['mythology']}</li>"
        for row in source_coverage(df)
    )
    contested = contested_breakdown(df)
    contested_items = "".join(
        f"<li>{_text(row['season_episode'])} · {escape(str(row['title']))} — "
        f"{_text(row['label_rationale'])}</li>"
        for row in contested
    )
    body = (
        "<main>"
        "<h1>Provenance & the disagreement</h1>"
        f"<p>Of {len(df)} records, {len(contested)} are contested — the sources "
        "disagree, or fewer than three cover them. Every figure is recomputed "
        "from the dataset.</p>"
        f"<h2>What each source covers</h2><ul>{coverage}</ul>"
        f"<h2>The contested records</h2><ul>{contested_items}</ul>"
        f'<p><a href="{BASE_URL}/provenance">Open the interactive dashboard</a></p>'
        "</main>"
    )
    return _page(
        "Provenance & the disagreement",
        "How the three classification sources cover and disagree about The "
        "X-Files episodes, with per-field provenance.",
        f"{BASE_URL}/provenance-text",
        body,
    )


def render_sitemap(df: pd.DataFrame) -> str:
    locs = [f"{BASE_URL}/overview", f"{BASE_URL}/provenance-text"]
    locs += [f"{BASE_URL}/seasons/{s}" for s in sorted(_seasons(df))]
    locs += [f"{BASE_URL}/episode/{record['id']}" for record in df.to_dict("records")]
    urls = "".join(f"<url><loc>{escape(loc)}</loc></url>\n" for loc in locs)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )


def robots_txt() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n"
