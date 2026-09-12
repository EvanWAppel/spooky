# The spooky dataset

**220 records**: all 218 television episodes of *The X-Files* (seasons 1–11)
plus the two feature films. Built offline by the pipeline in `build/`;
nothing is fetched at request time.

- **Source of truth:** `data/episodes/*.json` — one file per record,
  hand-editable, committed. The human layer (`logline`, `review_*`) is
  sacred: no pipeline step may overwrite a `human-reviewed` field.
- **Published artifacts:** `data/dist/spooky-episodes.json` and `.csv`
  (committed), plus `data/dist/spooky.sqlite` (regenerable build output
  with an FTS5 index — never committed, never edited).
- **Overrides:** `data/overrides/*.json` — hand-ruled inputs the pipeline
  consumes (film records, Fox DVD lists, creature flags, Wikidata
  dedupe rulings).

## License

The dataset is published under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
ShareAlike attaches from its Wikipedia and TVmaze inputs. Every record
carries per-field provenance naming the source and license; Wikipedia-derived
fields cite the exact article revision id.

## Field dictionary

| Field | Type | Source | License | Notes |
|---|---|---|---|---|
| `id` | string | derived | CC BY-SA 4.0 | `sSSeEE` for episodes, `film-YYYY` for films |
| `tvmaze_id` | int / null | TVmaze | CC BY-SA 4.0 | null for films |
| `season` | int / null | TVmaze | CC BY-SA 4.0 | null for films |
| `episode` | int / null | TVmaze | CC BY-SA 4.0 | null for films |
| `title` | string | Wikipedia | CC BY-SA 4.0 | canonical display title; TVmaze name where no article exists |
| `air_date` | date | TVmaze | CC BY-SA 4.0 | US theatrical release date for films |
| `production_code` | string / null | Wikipedia | CC BY-SA 4.0 | the only source carrying S10–11 codes; null for films |
| `runtime` | int | TVmaze | CC BY-SA 4.0 | |
| `rating` | float / null | TVmaze `rating.average` | CC BY-SA 4.0 | **never** an IMDb number; null for films |
| `label_fox_dvd` | enum / null | Fox Mythology DVD sets, via their Wikipedia articles | CC BY-SA 4.0 | `mythology` \| `not-listed`; **null = the sets don't cover it** (all of S10–11, both films) |
| `label_wikipedia` | enum / null | Wikipedia ‡ flag | CC BY-SA 4.0 | `mythology` \| `not-flagged` |
| `label_dom111` | enum / null | [dom111/xfiles-episode-picker](https://github.com/dom111/xfiles-episode-picker) | MIT wrapper, data CC BY-SA | `mythology` \| `motw`; null for films |
| `label_derived` | enum | derived | CC BY-SA 4.0 | `mythology` \| `monster-of-the-week` \| `standalone`; vote-based, null sources abstain |
| `label_contested` | bool | derived | CC BY-SA 4.0 | true when sources disagree **or** fewer than 3 cover the record |
| `label_rationale` | string | derived | CC BY-SA 4.0 | how `label_derived` was reached |
| `imdb_id` | string | Wikidata (P345) | CC0 | for linking to IMDb only |
| `wikidata_qid` | string / null | Wikidata | CC0 | |
| `enwiki_title` | string / null | Wikidata sitelink | CC0 | the episode's Wikipedia article |
| `tmdb_id` | int / null | constant (series 4087) | — | null for films |
| `tmdb_movie_id` | int / null | Wikidata (P4947) | CC0 | films only |
| `director` | list | TVmaze guest crew | CC BY-SA 4.0 | |
| `writers` | list | TVmaze guest crew | CC BY-SA 4.0 | union of Writer, Story, and Teleplay credits |
| `guest_cast` | list | TVmaze `/guestcast` | CC BY-SA 4.0 | names only — no images, no links |
| `tagline` | object | Wikipedia / derived | CC BY-SA 4.0 | opening-title-sequence tagline `{text, is_variant, broadcast_only, note_generated, note, review_status, reviewed_at, review_note}`; plain text, default `"The Truth Is Out There"`; `text` cites a Wikipedia revid for variants (PRD §7). CSV/SQLite flatten it to `tagline_text`, `tagline_is_variant` |
| `logline_generated` | string / null | machine draft | CC BY-SA 4.0 | ≤30 words; AI-drafted, machine-owned |
| `logline` | string / null | **the owner** | CC BY-SA 4.0 | ≤30 words; human-owned once reviewed |
| `review_status` | enum | the owner | CC BY-SA 4.0 | `unreviewed` \| `ai-drafted` \| `needs-work` \| `human-reviewed` — see below |
| `reviewed_at` | datetime / null | the owner | CC BY-SA 4.0 | |
| `review_note` | string / null | the owner | CC BY-SA 4.0 | |
| `provenance` | object | derived | CC BY-SA 4.0 | per-field `{source, license[, revid]}` |

### Review states

Descriptions move through one direction only, and the site badges which
layer a reader is seeing:

| State | Meaning | `logline` |
|---|---|---|
| `unreviewed` | no draft yet | null |
| `ai-drafted` | machine draft written to `logline_generated`, awaiting review | null |
| `needs-work` | the owner rejected the draft; `review_note` says why | null |
| `human-reviewed` | the owner approved or rewrote it — **sacred**, no pipeline step may overwrite it | the owner's text |

Only `human-reviewed` records have a populated `logline`. Everything else
displays `logline_generated` behind an "AI-drafted" badge.

Deliberately **absent**: synopses, plot recaps, transcripts, images, image
URLs, and IMDb ratings — see the legal constraints in `CLAUDE.md` and
`tests/test_legal.py`, which CI enforces against every committed record.

## Regenerating

```
uv run python -m build            # full pipeline, in order
uv run python -m build --only merge
uv run python -m build --only emit
```

Raw fetches land in `data/raw/` (gitignored). The merge refuses to touch
human-reviewed fields — it raises with a diff instead (`build/merge.py`,
`tests/test_review_guard.py`).
