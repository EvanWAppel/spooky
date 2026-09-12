# spooky — Product Requirements Document

> **spooky** — an X-Files episode data explorer. Codename from Mulder's academy
> nickname. Public portfolio piece by Evan Appel.
>
> Status: **Requirements complete.** Written 2026-07-26 via the RECL Requirements
> phase (AI interview, 9 rounds) plus a 57-agent adversarial feasibility study.
> Not yet executed.

---

## 1. What this is

A public, read-only web app for exploring data about *The X-Files* (1993–2018).
The headline view answers one question — **how did the show's balance of
mythology episodes vs. monster-of-the-week episodes change across eleven
seasons?** — and everything else hangs off that.

It is simultaneously a **portfolio piece**. A technical recruiter who has never
seen the show should understand what they're looking at within ten seconds, and
should come away thinking *this person builds real data products.*

### 1.1 Why it exists

Two goals, in priority order:

1. **Demonstrate data engineering judgment** — sourcing, licensing, provenance,
   reproducibility, handling of genuinely ambiguous classification.
2. **Be genuinely useful to an X-Files fan** — find episodes, sort them, build a
   watch order, go watch them.

Where these conflict, (1) wins. Specifically: surfacing that four sources
*disagree* about ~22 episodes is more valuable than picking one and pretending
the question is settled.

### 1.2 What it is not

- Not a wiki, not a fan encyclopedia, not a recap site.
- Not multi-user. No accounts, no login, no write path from the public web.
- Not live. Nothing is fetched from an API at request time.

---

## 2. Non-negotiable constraints

These came out of the feasibility research and are **not** design preferences.
Violating any of them is a legal problem, not a taste problem. Full detail in §11.

| # | Constraint |
|---|---|
| C1 | **No IMDb ratings or vote counts.** Republication into any online database is barred by IMDb's non-commercial license. OMDb cannot sublicense it. Linking to IMDb pages is fine. |
| C2 | **No show imagery of any kind.** No screencaps, stills, artwork, wordmark, or X-glyph. No hotlinked TVmaze images. |
| C3 | **No verbatim synopses or detailed plot recaps**, from any source, in any wording. |
| C4 | **No scraping or LLM ingestion** of Fandom, TV Tropes, IMDb, Pluto TV, or insidethex.co.uk. |
| C5 | **No episode transcripts.** |
| C6 | **CC BY-SA attribution is mandatory** and the derived dataset must carry ShareAlike. |
| C7 | **No Hulu deep-link collection.** Hulu's ToS bars scraping *and* unauthorized linking. |

---

## 3. Scope

### 3.1 Corpus

**220 records**: 218 television episodes (seasons 1–11) + 2 feature films.

- Seasons 1–9 (1993–2002), 202 episodes
- Seasons 10–11 (2016, 2018), 16 episodes
- *The X-Files: Fight the Future* (1998), *The X-Files: I Want to Believe* (2008)

**Films are first-class rows in the data, absent from the season chart.** They
have nullable `season`, `episode`, and `production_code`, are searchable and
classifiable, and surface in a separate Films card. The season chart shows only
the 218 episodes so that bar heights mean what they appear to mean.

**Out of scope:** *The Lone Gunmen*, *Millennium*, comics, novels, games.

### 3.2 Release plan

**v1 — the vertical slice.** Chart → click → table → detail panel → out-links.
Deployed, correct, tested, recruiter-legible.

| In v1 | Out of v1 |
|---|---|
| Ingest pipeline (all 220 records) | Viewership charts → **v2** |
| Ternary classification + per-source labels | Keyword playlists → **v2** |
| Stacked bar chart by season, click-to-filter | Layered search (tags/FTS/semantic) → **v2** |
| Sortable + filterable episode table | Trivia writeups → **v2** |
| Episode detail panel | People profiles → **v3** |
| TVmaze ratings + IMDb page links | Interconnections / connections to other works → **v3** |
| TMDB season watch links | Video extras → **dropped**, see §12 |
| AI-drafted loglines + review CLI | |
| Published CC BY-SA dataset | |
| Real URLs, responsive, WCAG AA | |

---

## 4. Stack and deployment

| Layer | Choice | Why |
|---|---|---|
| Language | Python ≥ 3.11, `uv` | CLAUDE.md governs the whole toolchain |
| App | Plotly Dash + Flask | Matches `mccoy`; Plotly click-callbacks are native |
| Serving | gunicorn, `Procfile` | Same as `mccoy` |
| Host | **Railway, always-on** | ~$5/mo |
| Domain | `spooky.evanappel.me` | |
| Repo | `github.com/EvanWAppel/spooky` | Exists, currently empty |
| Local path | `portfolio/spooky/` | Own git repo, nested; register in `projects.toml` |
| Source of truth | `data/episodes/*.json`, one file per record | Reviewable `git diff` — the whole point |
| Query artifact | SQLite, built, **not** committed as truth | FTS5 is free and v2 search wants it |
| Test | pytest, recorded fixtures + `@pytest.mark.network` | |
| Lint/type/hooks | ruff, ty, prek | |

### 4.1 On always-on

Railway sleeps after ~10 minutes idle, and the first request to a slept service
can return **502 Bad Gateway**. That lands on exactly the first-time visitor this
site exists to impress. **Do not enable serverless/sleep to save the $5.**

Known weakness accepted: Dash renders client-side, so episode text is invisible
to non-rendering crawlers. SEO is poor. A static-site migration (Observable
Framework or Next.js SSG on Cloudflare Pages) is the documented v2/v3 escape
hatch if that matters later.

---

## 5. Classification — the credibility spine

### 5.1 The problem

There is **no authoritative answer** to "is this episode mythology?" Four sources
give four counts:

| Source | Mythology count | Problem |
|---|---|---|
| Fox "Mythology" DVD box sets | ~60 | Predates the revival by a decade; omits "Musings of a Cigarette Smoking Man" |
| Wikipedia ‡ dagger flag | 71 daggered rows = **70 TV episodes + 1 film** | Revival flags are editorial, not sourced |
| `dom111/xfiles-episode-picker` (MIT) | 75 (143 MOTW) | One person's undocumented judgment |
| Assorted fan sites | ~80 | insidethex.co.uk forbids reproduction — **do not use** |

They agree on a hard core of ~60 and **disagree on ~22 episodes — 10% of the
show**, including "Musings of a Cigarette Smoking Man", "Christmas Carol"/"Emily",
and "The Gift".

### 5.2 The decision

**Ternary labels, with the disagreement rendered as a feature.**

Categories, exactly as they appear in the UI legend:

- **Mythology**
- **Monster-of-the-Week**
- **Standalone**

Each record stores **three independent source labels** plus a derived label:

```json
{
  "label_fox_dvd":    "mythology" | "not-listed" | null,
  "label_wikipedia":  "mythology" | "not-flagged" | null,
  "label_dom111":     "mythology" | "motw"       | null,
  "label_derived":    "mythology" | "monster-of-the-week" | "standalone",
  "label_contested":  true | false,
  "label_rationale":  "string — why derived landed where it did"
}
```

All three source labels are nullable. **`null` means the source does not cover
the record at all** — the Fox DVD sets predate the revival (all of seasons
10–11 are null there), and dom111 covers only the 218 TV episodes (both films
are null there). A null is *not* the same as `"not-listed"`/`"not-flagged"`,
which mean the source covered the record and declined to flag it. The UI
renders null as **"no data"** and never collapses the two.

`label_contested` is true wherever the available sources disagree **or fewer
than three sources cover the record**. Contested episodes render with a badge
in the table and a per-source breakdown in the detail panel:
*"Fox DVDs: not listed · Wikipedia: mythology · dom111: MOTW."*

**This is the single most important design decision in the project.** It converts
an unwinnable argument into the most interesting thing on the site.

### 5.3 Deriving `label_derived`

Deterministic, implemented in `spooky/classify.py` (called from
`build/merge.py`), fully unit-tested. **A null source label abstains** — it is
neither a yes nor a no. *(Decided 2026-07-27, DECISIONS.md OPEN-01. The
alternative — counting absence as "not mythology" — would let a source that
never saw the revival outvote the two that did.)*

1. **Votes** = the non-null values among the three source labels.
   `"not-listed"` and `"not-flagged"` are votes — negative ones.
2. `label_contested = true` whenever the votes disagree **or** there are fewer
   than 3 votes. Incomplete evidence is disclosed, never smoothed over.
3. **Zero votes → the build fails loudly** and demands a hand-ruled entry in
   `data/overrides/classification.json` (rationale required). No silent
   default. (No current record should hit this — films carry a Wikipedia
   vote — so reaching it means the ingest broke.)
4. A strict majority of votes says mythology → `mythology`.
5. Otherwise: the episode features a non-recurring paranormal antagonist
   (`has_creature`) → `monster-of-the-week`; else → `standalone`. Ties (1–1)
   land here, contested via rule 2.

Rule 5 needs a `has_creature` boolean. It is **not** derivable from any source
and must be hand-maintained in `data/overrides/creature.json`, seeded by an AI
pass over factual credits/titles and then confirmed by the owner through the
review CLI. Every assignment records how it was reached in `label_rationale`.

Consequences worth naming, because they will show in the chart:

- **Every season 10–11 episode is contested** (2 votes — the Fox DVDs abstain).
  Honest: the revival's classification rests on thinner evidence.
- ***Fight the Future* derives `mythology`** from its single Wikipedia vote
  (contested, 1 vote). This resolves the old rules' contradiction with §8.1
  step 07 — no film special case exists anymore.
- Under the old rules a lone mythology vote forced `monster-of-the-week`;
  now the `has_creature` flag decides MOTW vs standalone for those episodes,
  which is what the flag is for.

> **Open item for the Execute phase:** the ~60/70/71/~80 counts above must be
> **re-derived at build time**, not trusted. Wikipedia's tables are transcluded
> and shift without the list page being edited.

---

## 6. Features — v1

### F1. Season classification chart *(the headline)*

Stacked vertical bar chart. One bar per season (1–11), three stacked segments
(Mythology / Monster-of-the-Week / Standalone), **absolute counts**.

- Clicking a **segment** filters the table to that season *and* that category.
- Clicking a **season axis label** filters to the whole season.
- Selection is reflected in the URL and in a clearable filter chip.
- Absolute counts, not percentages — seasons 10 (6 eps) and 11 (10 eps) must
  visibly be small. A 100% view is v2.
- Colorblind-safe three-colour categorical palette. Not red/green.

### F2. Episode table

Columns: **Season/Ep · Title · Air date · Category · TVmaze rating**, plus two
link buttons per row.

- Sortable on every column. Filterable by season, category, contested-only,
  and a title text filter.
- Contested episodes carry a visible badge.
- Default sort: season, then episode.
- All 220 records reachable; films appear only when no season filter is active.
- Sort and filter state lives in the URL.

### F3. Episode detail panel

Opens on row click, as a side panel.

Contains: title, season/episode, air date, production code, **logline**,
director, writer(s) (union of Writer / Story / Teleplay), guest cast, category
with per-source breakdown when contested, TVmaze rating, and the two out-links.

Also renders the **review status badge** — `AI-drafted` or `human-reviewed` —
on the logline. This is deliberately public: the editorial process is part of
what's being demonstrated.

### F4. Out-links

Two per episode:

- **IMDb page** — `imdb.com/title/{imdb_id}/`, from Wikidata P345. Linking is
  unrestricted. The rating shown on *our* page is TVmaze's, never IMDb's.
- **Where to watch** — the TMDB **show-level** watch page,
  `themoviedb.org/tv/4087-the-x-files/watch`. Sanctioned, provider-agnostic,
  auto-updates as rights move, survives the Hulu→Disney+ merger expected
  late 2026. *(Corrected 2026-07-27 at G-05: research specified a season
  watch page, but `/season/{n}/watch` 404s on every season — TMDB has no
  season-level watch pages. Verified live against all 11.)*

Films link to their own TMDB watch pages. Neither film is currently on any
streaming service — the link must degrade gracefully.

### F5. Loglines + review CLI

Every record carries a **logline: an original description, hard-capped at 30
words.** Not a synopsis. Not a recap. See C3.

Pipeline drafts one per record from *factual* inputs only (title, credits,
air date, classification, Wikipedia Production/Themes section). The owner
promotes each to `human-reviewed` via:

```bash
uv run python tools/review.py
```

The CLI walks unreviewed records one at a time, shows the draft plus its
sources, and accepts approve / edit / reject-with-note. It writes back to
`data/episodes/*.json`.

**Edits are sacred.** Generated and human-owned text live in separate fields:

```json
{
  "logline_generated": "machine-owned, may be regenerated freely",
  "logline":           "human-owned once review_status is human-reviewed",
  "review_status":     "ai-drafted" | "human-reviewed" | "needs-work",
  "reviewed_at":       "ISO-8601 or null",
  "review_note":       "string or null"
}
```

No pipeline step — including the scheduled refresh — may write `logline` when
`review_status == "human-reviewed"`. If regeneration would change it, the
pipeline emits a diff and changes nothing. This is enforced by a test.

v1 ships when **all 220 loglines are `human-reviewed`.**

### F6. Published dataset

`data/dist/spooky-episodes.{json,csv}` — the merged 220-record dataset with
per-field provenance, plus `data/README.md` carrying a full field dictionary,
source, and license per field. Published CC BY-SA 4.0, satisfying the
ShareAlike obligation and standing on its own as a portfolio artifact.

---

## 7. Features — v2 and beyond

Specified here so the v1 data model doesn't foreclose them.

### v2

- **Opening-title taglines — the intro that means something.** *(Owner-requested
  2026-09-11.)* The X-Files title sequence always ends on a card reading **"The
  Truth Is Out There."** In a documented minority of episodes Chris Carter swaps
  it for an episode-specific line — "Trust No One" (Deep Throat's dying words, the
  S1 finale), "Apology is Policy" (731), "Everything Dies" (Herrenvolk), the
  Navajo "Éí 'Aaníígóó 'Áhoot'é" (Anasazi), "E Pur Si Muove" (Biogenesis), and
  more. The swap is an authorial signal, and *which* episodes get one — and what
  it says — is exactly the kind of fandom detail this project can surface **as
  data** rather than as recap. Three surfaces:
  1. **Per episode** — a `tagline` on every record. Variant episodes carry a
     badge in the table and, in the detail panel, the tagline (plain text) plus a
     short owner-written gloss on why it changed.
  2. **A "tagline variants only" filter**, URL-encoded like the contested toggle.
  3. **A dedicated *Taglines* view** — a chronological catalogue of every variant
     episode with its line and gloss, each linking to the episode. This is the
     community-facing centrepiece.
  - **Data model** (proposed; a nested object avoids colliding with the logline's
    top-level `review_status`):
    ```json
    "tagline": {
      "text":           "Apology is Policy",   // verbatim opening-credits line, plain text; default "The Truth Is Out There"
      "is_variant":     true,                  // DERIVED at build: normalized(text) != normalized(default). Never hand-set.
      "broadcast_only": null,                  // true where the variant aired but the DVD reverts to default (Wikipedia-documented; else null)
      "note_generated": "…",                   // machine-drafted gloss, variants only
      "note":           null,                  // owner-owned gloss, human-reviewed
      "review_status":  "ai-drafted",          // "ai-drafted" | "human-reviewed" | "needs-work" | "not-applicable" (defaults)
      "reviewed_at":    null,
      "review_note":    null
    }
    ```
  - **Source discipline.** `tagline.text` comes from **Wikipedia only** — each
    variant is documented in the article's *Production* / *Conception and writing*
    section, which step 06 already fetches (verified live against *Anasazi* and
    *731*, 2026-09-11). **Absence of a documented change means the default**, not
    missing data. **Never** take taglines from Fandom, TV Tropes, or IMDb "crazy
    credits" (C4) — a naive web search surfaces exactly those first. The gloss is
    original writing grounded in the fetched section, inline-cited, and routed
    through the same review CLI as loglines. **Do not re-derive a count of
    variants into this document** — the build prints it.
  - **Legal.** Taglines ship as **plain site text** — short factual phrases, the
    same posture already taken for episode titles and "The X-Files." They must
    **never** be rendered in the show's title-card typography, glow, or as an
    image; that would implicate C2. Foreign-language taglines are captured
    verbatim; their English translation is contested between sources (see §13) and
    treated as optional, owner-supplied, and flagged — disclosure, not resolution,
    in the house style.

- **Viewership charts.** Deferred because **every viewership claim in the
  research failed verification.** The Wikipedia "U.S. viewers (millions)" column
  requires full hand-QA before it may be charted. When built: Live+SD as the
  primary series across all eleven seasons, with season 10's Live+7 overlaid and
  explicitly labeled — the Nielsen currency change becomes the point rather than
  a hidden distortion. Annotate "Leonard Betts" (29.15M, post-Super Bowl) so the
  spike reads as context, not a bug. Seasons 1–2 rest on 1993–95 print USA Today
  citations with no URL.
- **Keyword playlists.** In-app ordered watch queue, per-row watch links, progress
  checkboxes, playlist state encoded in the URL for sharing and bookmarking,
  export to CSV/Markdown. No account, no database. Hulu has no playlist API and
  none is attempted.
- **Layered search**, powering playlists — three layers, results merged and
  labeled with *why* they matched:
  1. **Curated tags** (`cryptid`, `government-conspiracy`, `body-horror`,
     `religious`, `comedy`, …), AI-proposed and owner-reviewed through the same
     review CLI.
  2. **Full-text** over titles, loglines, and tags via SQLite FTS5.
  3. **Semantic** over embeddings, so "cryptids" finds the Flukeman without the
     word appearing anywhere.
- **Trivia writeups.** Longer per-episode pieces with embedded Wikipedia links.
  **Wikipedia only** — Fandom's ToU bars AI ingestion and IMDb trivia is barred
  outright. Grounded strictly in the fetched `Production` and `Themes` sections,
  every claim carrying an inline source link, all flowing through the same
  AI-drafted → human-reviewed pipeline as loglines.
- **100% stacked toggle** on the season chart.

### v3

- **People profiles** — writers, directors, and recurring guest actors, with
  outbound links and their episode list. **343 recurring actors** identified
  (a verifier corrected an earlier claim of 345). Note: producer credits exist
  only at series level in TVmaze; TMDB has per-episode producer credits but
  coverage is sparse. TMDB's series-level `episode_count` is demonstrably wrong
  (lists Glen Morgan as EP for all 218; actual is 16) and must not be used.
- **Interconnections** — an episode→episode graph built from Wikipedia's ~1,217
  inter-article wikilinks. Edges are facts; the gloss is written by the owner.
- **Connections to outside works** — films, books, music, historical events.
  Least structured data in the whole brief; hand-curated or LLM-extracted from
  Wikipedia only.
- **Static-site migration**, if SEO becomes a priority.

---

## 8. Data pipeline

Run offline, output committed. **Nothing is fetched at request time.** Every
Wikimedia request carries a descriptive User-Agent with contact info — generic
agents get blocked without notice.

```
build/                 (a package: __init__.py + one module per step)
  spine.py      TVmaze          → data/raw/tvmaze_episodes.json
  wikipedia.py  MediaWiki parse → data/raw/wiki_seasons/*.json
  wikidata.py   SPARQL          → data/raw/wikidata.json
  labels.py     dom111 (pinned) → data/raw/dom111.json
  people.py     TVmaze          → data/raw/guestcast.json, guestcrew.json
  articles.py   Special:Export  → data/raw/articles.xml
  merge.py      → data/episodes/*.json   ← SOURCE OF TRUTH, committed
  loglines.py   Anthropic API   → logline_generated field
  emit.py       → data/dist/*.{json,csv} + spooky.sqlite
  __main__.py   the driver: runs the steps in exactly the order above
```

Run order lives in `build/__main__.py` (`uv run python -m build`, or
`-m build --only spine` for one step) — **not** in the filenames. The modules
were originally numbered `01_spine.py` … `09_emit.py`, but a Python identifier
cannot start with a digit, so numbered modules can't be imported by tests —
which would have made every pipeline test in Groups D–F impossible to write.

### 8.1 Step notes — these are landmines, not suggestions

**01 — spine.** `GET https://api.tvmaze.com/shows/430/episodes`. One call, no
key, 218 records. **Do not pass `?specials=1`** — it returns 222 and breaks the
count. Key everything on the TVmaze `id`.

**02 — Wikipedia.** 11 serial requests to
`action=parse&page=The X-Files season N&prop=wikitext`, throttled to ~1 req/sec
(parallel fetching returns 429).

- Use a **brace-balanced template extractor, not a regex.** A naive regex
  silently drops all 16 season 10–11 rows.
- Match the mythology flag **case-insensitively** on `/double[- ]dagger/i`
  against the `RTitle` field, not `Title`. Season 3 uses a different template
  capitalization; a case-sensitive match silently drops 7 episodes.
- Split multi-values on `<hr>`.
- **Do not parse `List_of_The_X-Files_episodes`** — it transcludes the season
  pages, and its own wikitext contains only the two film rows.

**03 — Wikidata.** One SPARQL query, CC0, no obligations. Use for the ID spine
only: enwiki title, IMDb ID (P345), TMDB ID. Expect ~219 items — "The Truth"
appears three times; reconcile by hand.

**04 — labels.** Fetch the dom111 raw JSON once and **pin the blob SHA.**
143 MOTW + 75 mythology, zero nulls — fully verified. MIT-licensed wrapper, but
it cannot relicense the underlying TVmaze CC BY-SA data; attribute both.

**05 — people.** 218 `/guestcast` + 218 `/guestcrew` calls, throttled ~20/10s.
**Budget an explicit retry pass** — a naive sweep silently loses 10–15 episodes
to transient failures. Parse crew as the **union of `Writer`, `Story`, and
`Teleplay`**; filtering on `guestCrewType == "Writer"` alone drops 11 episodes.

**06 — articles.** **One** `Special:Export` POST with all 214 titles,
`curonly=1` → ~4.1 MB XML. Do not fire 214 individual `action=parse` calls; half
will 429. Record the revision ID per article so attribution points at an exact
version.

**07 — merge.** Two-parter policy, decided once: TVmaze splits "The Truth" into
(1)/(2) → 218 rows; Wikipedia merges it → 217. **Take TVmaze's shape (218)** and
duplicate Wikipedia's merged values across both rows. Special-case the title
join for `The Sixth Extinction II: Amor Fati` (Wikipedia) vs
`The Sixth Extinction: Amor Fati` (TVmaze), or the join reports a spurious miss.
Films are hand-entered from Wikipedia with nullable season/episode/production
code; Wikipedia flags *Fight the Future* as mythology and *I Want to Believe*
as not.

**Taglines *(v2, step notes for the future fetcher)*.** Do **not** add a network
step — the opening-title tagline is documented inline in each article's
*Production* / *Conception and writing* prose, which step 06 already captures in
`data/raw/article_sections.json` (D-14). The tagline fetcher scans that text for a
documented change; when none is documented, the episode carries the **default**,
and that is a fact, not a gap. Record the Wikipedia revision id per variant.
**Re-derive the variant set — never hard-code it.** Non-English taglines
(Anasazi's Navajo line) are captured verbatim; their translation is contested, so
it lives in the owner gloss, not in `tagline.text`.

### 8.2 Field ownership

| Field | Source | License |
|---|---|---|
| `tvmaze_id`, `season`, `episode`, `air_date`, `runtime` | TVmaze | CC BY-SA |
| `title` (canonical) | Wikipedia | CC BY-SA |
| `production_code` | **Wikipedia only** — no API has these for S10/S11 | CC BY-SA |
| `director`, `writer` / `story` / `teleplay` | Wikipedia primary, TVmaze cross-check | CC BY-SA |
| `rating` | TVmaze `rating.average` | CC BY-SA |
| `label_wikipedia` / `label_dom111` / `label_fox_dvd` | respective | mixed |
| `guest_cast` (~2,744 rows) | TVmaze `/guestcast` | CC BY-SA |
| `imdb_id`, `tmdb_id`, `wikidata_qid` | Wikidata | CC0 |
| `us_viewers_millions` *(v2)* | Wikipedia — **unverified, hand-QA required** | CC BY-SA |
| `logline` | **the owner** | owner's |
| `label_derived`, all computed metrics | derived | owner's |
| `tagline.text` *(v2)* | **Wikipedia only** — Production / Conception section | CC BY-SA |
| `tagline.is_variant`, `tagline.broadcast_only` *(v2)* | derived at build | owner's |
| `tagline.note` *(v2)* | **the owner** | owner's |
| synopsis, images | **deliberately omitted** | — |

### 8.3 Scheduled refresh

A monthly GitHub Action re-runs steps 01–07 and opens a PR with the data diff.
Secrets live in GitHub Actions.

**The refresh may only touch machine-owned fields.** It must never write a field
whose `review_status == "human-reviewed"`. A test asserts this, and the job fails
loudly rather than silently skipping (see CLAUDE.md: *do not hide or wrap errors*).

---

## 9. UX and design

**Restrained modern with subtle X-Files signals.** Reads first as a serious data
tool — dark theme, clean typography, excellent charts — with quiet nods to the
show. Takeaway: *this person builds real data products*, with the fandom as
charm rather than pitch.

Because C2 forbids all show imagery, the visual identity must be carried
entirely by **type, colour, layout, and original SVG/CSS**. Episode-as-glyph
grids and arc timelines instead of stills. **Do not derive a palette from actual
frames.**

### 9.1 Routing

Real URLs from day one. State encodes into the URL: season, category filter,
sort, text filter, and selected episode. `/season/4?category=motw&sort=rating`
must be linkable. This is the foundation v2's shareable playlists need, and
retrofitting routing later is painful.

### 9.2 Accessibility

Responsive and WCAG AA, designed in rather than retrofitted:

- Colorblind-safe categorical palette for the three-segment stacked bar.
- Full keyboard navigation of chart, table, and panel.
- Chart has a data-table alternative for screen readers.
- Contrast AA on all text.
- Works on a phone — recruiters open links on phones.

---

## 10. Definition of done — v1

Verifiable, not vibes. All must hold:

1. Live at `spooky.evanappel.me`, always-on, **no 502 on first request.**
2. All 220 records present; counts re-derived at build time, not hard-coded.
3. Classifications spot-checked by the owner against the Fox DVD lists;
   all contested episodes carry a rationale.
4. All 220 loglines `human-reviewed`.
5. Chart → click → table filter works for every season and every category.
6. Both out-links resolve correctly for a sample of 10 episodes and both films.
7. `uv run pytest` green. `uv run ruff check .` clean. `uv run ty check` clean.
   `prek` installed and passing.
8. Published dataset + `data/README.md` field dictionary present and accurate.
9. Responsive and AA-clean.
10. **Recruiter legibility:** someone with no X-Files knowledge understands what
    they're looking at within ten seconds, and the README explains data
    provenance clearly.

---

## 11. Legal, licensing, attribution

### 11.1 Safe / not safe

**Safe to ship:** all facts (titles, numbers, air dates, production codes,
director/writer names, runtimes); TVmaze ratings and guest-cast rows with
attribution; Wikipedia-derived structured fields with attribution; the owner's
own loglines and every computed metric; the episode→episode connection graph
(edges are facts); "The X-Files" as plain text; opening-title taglines as plain
text (short factual phrases, the same posture as titles — see §7, and never
rendered in the show's title-card typography or as an image, which would implicate
C2); a takedown contact.

**Not safe — see §2.**

### 11.2 Required footer — verbatim

> Episode metadata and ratings from [TVmaze](https://www.tvmaze.com), licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Additional episode data derived from [Wikipedia](https://en.wikipedia.org/wiki/List_of_The_X-Files_episodes), licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); modified. Identifier data from [Wikidata](https://www.wikidata.org) (CC0). Mythology/monster-of-the-week labels adapted from [dom111/xfiles-episode-picker](https://github.com/dom111/xfiles-episode-picker) (MIT). The derived dataset published here is licensed CC BY-SA 4.0.
>
> This is an unofficial fan project. It is not affiliated with, endorsed by, or approved by 20th Television, The Walt Disney Company, or Ten Thirteen Productions. *The X-Files* and all related marks are the property of their respective owners. Contact: appelew@gmail.com

Because v1 uses TMDB watch links, also add — with the TMDB logo less prominent
than the site's own branding:

> This website uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

*Not legal advice. Warhol (2023) and Jack Daniel's (2023) both tightened the
ground under fan-adjacent projects.*

### 11.3 Nuances worth keeping straight

- *Feist* does **not** say facts are unconditionally free — the rule is
  conditional on the competing work not reproducing the same **selection and
  arrangement**. Re-derive facts from multiple sources; don't mirror one
  provider's structure. And copyright status says nothing about the **contract**
  accepted to obtain the data.
- The no-imagery posture is **risk management, not settled law.** §106 is
  expressly subject to §107, and fair use has protected screenshots in court.
  We decline imagery by choice, not because it is categorically unlawful.

### 11.4 API keys

Needed: **Anthropic** only (logline drafting, Group F). Offline-only, in local
`.env`, plus a GitHub Actions secret if the scheduled refresh ever regenerates
drafts.

**No longer needed:**

- **TMDB** *(corrected 2026-07-27)* — the pipeline as built uses TVmaze,
  Wikipedia, and Wikidata; the TMDB watch links are static URLs constructed
  without any API call. A TMDB key returns only if v2/v3 features need the
  API (e.g. per-episode producer credits).
- OMDb (IMDb ratings are barred — C1) and YouTube Data API (video extras
  dropped — §12).

---

## 12. Explicitly dropped

**Video / behind-the-scenes extras.** Every claim in this research area failed
verification: the X-Cast RSS coverage numbers, the YouTube quota model, the
30-day cache rule, and keyless embedding. Official YouTube BTS content covers
roughly five items, all from the 2016 revival; the remainder is fan-uploaded
rips with active link-rot. Not worth a pipeline. Revisit only with independent
verification.

**Fandom / The X-Files Wiki.** Richest trivia source available, citing official
books with page numbers — and its ToU bars automated collection *and* AI
ingestion specifically. The only lawful path is reading manually for leads and
independently verifying each. Skipped by choice.

**Contemporary review sentiment analysis.** The research agent covering this
topic **failed with a network error and produced nothing.** The feature is
therefore *unassessed*, not rejected. Do not build it until that research is
redone. Wikipedia's per-episode "Reception" sections are the likely lawful
substrate.

---

## 13. Known unknowns

Carried forward deliberately. **Do not build on these without re-deriving.**

**Unverified — verifier errored, treat as unknown:**
- The Wikipedia 217-row parse and its field-population rates.
- TMDB `/tv/4087` schema specifics; Wikidata SPARQL field counts.
- **All four viewership claims** — hence viewership is v2 and gated on hand-QA.
- All four video-extras claims — hence dropped.

**Actively refuted — corrected here:**
- ~~"Wikipedia flags 70 rows = 71 episodes"~~ → **71 daggered rows = 70 TV
  episodes + 1 film.** No row contains two daggers.
- ~~"Pluto TV has a public unauthenticated API"~~ → returns 401
  `BearerTokenRequired`; its ToU also restricts linking and bars database storage.
- ~~"$150,000/yr is the only compliant IMDb route"~~ → the IMDb Ratings bulk
  product is **$50,000/yr** with a free 1-month trial. Still impractical, but for
  cost reasons, not availability.
- ~~"345 recurring actors; must key on person_id not name"~~ → **343**, and in
  this dataset names and person_ids are exactly equivalent (1,828 ↔ 1,828).
- ~~"Producer credits aren't available per-episode anywhere"~~ → TMDB *does*
  support them; coverage is just sparse. TVmaze `/guestcrew` is guest-scoped by
  design.
- ~~"The Hurwitz & Knowles book sources the dagger flag"~~ → it appears only in a
  footnote about one exception ("The Gift").

**Shaky but not refuted:** Trakt's commercial-use permission rests on a staff
forum post, not a written license. The dom111 labels are one person's
undocumented judgment. IMDb's "publishing is commercial" reading comes from a
single 2023 support-forum reply about a *mobile app*, not a website — reasonable
but not airtight.

**Tagline data (v2), handled by disclosure not resolution:** which episodes revert
to the default tagline on DVD versus the broadcast cut is only partially
documented on Wikipedia (`tagline.broadcast_only` stays `null` where unknown); and
the English translation of the Navajo ("Anasazi") and other non-English taglines
is contested between sources — even Wikipedia's own gloss ("The Truth is Out
There") differs from the common fan translation ("The truth is far from here").
Capture the line verbatim in `tagline.text`; leave the translation to the flagged
owner gloss.

---

## 14. Provenance of this document

Produced in the **Requirements** phase of RECL (Matt Harrison, PyCon 2026):
Requirements → Execute → Check → Loop.

- 9 rounds of structured interview, 36 decisions.
- One 57-agent adversarial feasibility workflow (~3.1M tokens, 1,321 tool calls,
  49 minutes). 44 agents completed, **13 failed on network errors** — coverage
  gaps are recorded in §12 and §13 rather than papered over.
- Research **overturned four already-agreed decisions** (IMDb ratings, Hulu deep
  links, Railway sleep, episode synopses) before any code was written. That is
  the intended function of front-loading feasibility into Requirements.

Companion documents: `CLAUDE.md` (standing rules), `TASKS.md` (execution plan),
`HANDOFF.md` (cold-start context for another agent), `POSTMORTEM.md` (living
process evaluation).
