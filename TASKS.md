# spooky — Task List

Execution plan for `PRD.md`. Read `CLAUDE.md` first — its project-specific rules
are legal constraints, not style preferences.

**Legend:** `[ ]` pending · `[~]` in progress · `[x]` done

**Every task carries a `Verify:` line.** Run it and paste the real output. The
Check phase belongs to the human — leave evidence, never "should work."

**Parallelism.** Groups A, B, and D can start immediately and run concurrently.
Group C is the highest-priority path and should be staffed first. A group's
dependencies are stated under its heading; never start a group whose
dependencies are unmet.

```
A ─┬─────────────────────────────────────────────► H ──► I ──► J
B ─┤                                               ▲     ▲     ▲
   └─► C (VERTICAL SLICE — do this first) ─────────┤     │     │
D ─────► E ─────► G ───────────────────────────────┴─────┘     │
              F ───────────────────────────────────────────────┘
```

---

## Group A — Scaffold & Infra
> No dependencies. Start immediately. Safe to run alongside B and D.

- [x] **A-01** `uv init` in `portfolio/spooky/`; set `requires-python = ">=3.11"`, `name = "spooky"` in `pyproject.toml`
  - Verify: `uv run python -c "import sys; print(sys.version)"` → 3.11 or higher
- [x] **A-02** Add runtime deps: `uv add dash plotly flask gunicorn pandas httpx python-dotenv`
  - Verify: `uv run python -c "import dash, plotly, httpx, pandas; print('ok')"` → `ok`
- [x] **A-03** Add dev deps: `uv add --dev pytest pytest-mock ruff ty prek respx`
  - Verify: `uv run pytest --version` and `uv run ruff --version` both print versions
- [x] **A-04** Create `.env.example` with `TMDB_API_KEY=`, `ANTHROPIC_API_KEY=`, `FLASK_SECRET_KEY=`, `WIKI_USER_AGENT=spooky/0.1 (appelew@gmail.com)`
  - Verify: `cat .env.example` shows all four keys with empty values
- [x] **A-05** Create `.gitignore`: `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.env`, `.env.*`, `!.env.example`, `.DS_Store`, `data/raw/`, `*.sqlite`
  - Verify: `git status --porcelain` shows no `.env`, no `data/raw/`, no `.venv`
- [x] **A-06** Copy `../templates/python/ruff.toml` and `../templates/python/pre-commit-config.yaml` into the repo; adjust names to `spooky`
  - Verify: `uv run ruff check .` exits 0
- [x] **A-07** Install prek hooks: `uv run prek install`
  - Verify: `uv run prek run --all-files` exits 0
- [x] **A-08** Create `Procfile`: `web: gunicorn app:server --bind 0.0.0.0:$PORT`
  - Verify: `cat Procfile` matches exactly
- [x] **A-09** Create directory skeleton with `.gitkeep` files: `build/`, `data/episodes/`, `data/overrides/`, `data/dist/`, `components/`, `tools/`, `tests/fixtures/`
  - Verify: `find . -name .gitkeep -not -path './.venv/*' | wc -l` → 7
- [x] **A-10** Create `spooky/logging_config.py` exposing `setup_logging(level)` using stdlib `logging`, format `%(asctime)s %(levelname)s %(name)s %(message)s`. No exception swallowing anywhere.
  - Verify: `uv run python -c "from spooky.logging_config import setup_logging; setup_logging('DEBUG'); import logging; logging.getLogger('t').debug('hi')"` prints a DEBUG line
- [x] **A-11** `git init`, initial commit, add remote `https://github.com/EvanWAppel/spooky.git`, create branch `init-scaffold`. **Do not push to main** (CLAUDE.md).
  - Verify: `git remote -v` shows the spooky remote; `git branch --show-current` is not `main`
- [x] **A-12** Add `spooky` entry to `../projects.toml`: language `python`, runtime `uv`, host `railway`, domain `spooky.evanappel.me`, tags `["portfolio"]`, status `wip`, dev/test/lint commands
  - Verify: `uv run python -c "import tomllib;d=tomllib.load(open('../projects.toml','rb'));print(d['projects']['spooky']['domain'])"` → `spooky.evanappel.me`
- [x] **A-13** Copy `../templates/python/.github/workflows/ci.yml`; ensure CI runs `pytest -m "not network"`, `ruff check`, `ty check`
  - Verify: `grep -c 'not network' .github/workflows/ci.yml` → at least 1

---

## Group B — Test Scaffolding & Fixtures
> Depends on: A-01, A-03. Runs alongside A and D. TDD red phase — these are written before implementation.

- [ ] **B-01** Create `tests/conftest.py` with fixtures: `sample_tvmaze_episode`, `sample_wiki_season_wikitext`, `sample_wikidata_row`, `sample_dom111_record`, `tmp_data_dir`
  - Verify: `uv run pytest --fixtures tests/ | grep -c sample_` → at least 4
- [ ] **B-02** Record a real TVmaze payload once into `tests/fixtures/tvmaze_episodes.json` via a one-off script; commit it
  - Verify: `uv run python -c "import json;d=json.load(open('tests/fixtures/tvmaze_episodes.json'));print(len(d))"` → 218
- [ ] **B-03** Record real Wikipedia wikitext for **season 3 and season 10** into `tests/fixtures/wiki_s03.txt` and `wiki_s10.txt`. These two are the known edge cases (S3 template capitalization, S10 revival rows).
  - Verify: both files exist and are non-empty; `grep -ci 'double.dagger' tests/fixtures/wiki_s03.txt` → at least 1
- [ ] **B-04** Write `tests/test_spine.py` — `fetch_episodes()` returns 218 records, each with `id`, `season`, `number`, `airdate`, `rating`
  - Verify: `uv run pytest tests/test_spine.py -q` → fails (red), function not implemented
- [ ] **B-05** Write `tests/test_spine.py` — asserts the request URL contains **no** `specials=1` parameter
  - Verify: `uv run pytest tests/test_spine.py -q` → fails (red)
- [ ] **B-06** Write `tests/test_wikipedia.py` — brace-balanced extractor returns **16 rows** from the combined S10+S11 fixture (regex-based parsers drop these)
  - Verify: `uv run pytest tests/test_wikipedia.py -q` → fails (red)
- [ ] **B-07** Write `tests/test_wikipedia.py` — dagger detection is case-insensitive, matches `/double[- ]dagger/i` on `RTitle`, and finds all flagged rows in the S3 fixture
  - Verify: `uv run pytest tests/test_wikipedia.py -q` → fails (red)
- [ ] **B-08** Write `tests/test_wikipedia.py` — multi-value fields split on `<hr>` into a list
  - Verify: `uv run pytest tests/test_wikipedia.py -q` → fails (red)
- [ ] **B-09** Write `tests/test_classify.py` — all five `label_derived` rules from PRD §5.3, one test per rule, plus `label_contested` set correctly for each
  - Verify: `uv run pytest tests/test_classify.py -q` → fails (red), 6+ tests collected
- [ ] **B-10** Write `tests/test_merge.py` — "The Truth" resolves to **2 rows** (TVmaze shape) with Wikipedia values duplicated across both
  - Verify: `uv run pytest tests/test_merge.py -q` → fails (red)
- [ ] **B-11** Write `tests/test_merge.py` — `The Sixth Extinction II: Amor Fati` (Wikipedia) joins to `The Sixth Extinction: Amor Fati` (TVmaze) without a reported miss
  - Verify: `uv run pytest tests/test_merge.py -q` → fails (red)
- [ ] **B-12** Write `tests/test_review_guard.py` — **the sacred-edits test.** Any merge/refresh run must raise rather than modify `logline` when `review_status == "human-reviewed"`
  - Verify: `uv run pytest tests/test_review_guard.py -q` → fails (red)
- [ ] **B-13** Write `tests/test_legal.py` — asserts no record contains a `synopsis` or `image` key, and no field value exceeds the 30-word logline cap
  - Verify: `uv run pytest tests/test_legal.py -q` → fails (red)
- [ ] **B-14** Add `network` marker to `pyproject.toml` under `[tool.pytest.ini_options]` with `markers = ["network: hits real APIs, excluded from CI"]`
  - Verify: `uv run pytest -m network --collect-only -q` runs without an unknown-marker warning

---

## Group C — VERTICAL SLICE (fixture data) ⚡
> Depends on: A-01…A-10. **Highest priority — staff this first.**
> Uses a hand-entered 12-episode fixture so the whole pipe is proven and deployed
> before the real ingest exists. Do not wait for Group D/E.

- [ ] **C-01** Hand-create `data/episodes_sample/` with **12 records** — 4 mythology, 4 MOTW, 4 standalone, spanning seasons 1, 5, and 10, including one contested episode. Full schema per PRD §5.2 and §8.2, loglines written by hand.
  - Verify: `uv run python -c "import json,glob;fs=glob.glob('data/episodes_sample/*.json');print(len(fs))"` → 12
- [ ] **C-02** Write `tests/test_loader.py` — `load_episodes(path)` returns a DataFrame with the full column set and correct dtypes
  - Verify: `uv run pytest tests/test_loader.py -q` → fails (red)
- [ ] **C-03** Implement `spooky/loader.py::load_episodes(path)` reading `*.json` into a pandas DataFrame
  - Verify: `uv run pytest tests/test_loader.py -q` → passes (green)
- [ ] **C-04** Write `tests/test_chart.py` — `build_season_chart(df)` returns a `plotly.graph_objects.Figure` with exactly 3 traces named `Mythology`, `Monster-of-the-Week`, `Standalone`
  - Verify: `uv run pytest tests/test_chart.py -q` → fails (red)
- [ ] **C-05** Implement `components/chart.py::build_season_chart(df)` — stacked bar, absolute counts, one bar per season, **films excluded**, colorblind-safe palette (not red/green)
  - Verify: `uv run pytest tests/test_chart.py -q` → passes (green)
- [ ] **C-06** Write `tests/test_chart.py` — films are absent from the chart even when present in the input DataFrame
  - Verify: `uv run pytest tests/test_chart.py -q` → passes
- [ ] **C-07** Write `tests/test_table.py` — `build_episode_table(df)` returns a `dash.dash_table.DataTable` with columns Season/Ep, Title, Air date, Category, TVmaze rating
  - Verify: `uv run pytest tests/test_table.py -q` → fails (red)
- [ ] **C-08** Implement `components/table.py::build_episode_table(df)` — sortable on all columns, `sort_action="native"`, `filter_action="native"`, contested badge column
  - Verify: `uv run pytest tests/test_table.py -q` → passes (green)
- [ ] **C-09** Write `tests/test_links.py` — `imdb_url(imdb_id)` → `https://www.imdb.com/title/{id}/`; `tmdb_watch_url(season)` → `https://www.themoviedb.org/tv/4087-the-x-files/season/{n}/watch`; films use their own TMDB movie watch URL; `None` inputs return `None` rather than a broken URL
  - Verify: `uv run pytest tests/test_links.py -q` → fails (red)
- [ ] **C-10** Implement `spooky/links.py` per C-09. **No Hulu URL construction anywhere** (CLAUDE.md C7).
  - Verify: `uv run pytest tests/test_links.py -q` → passes; `grep -ri "hulu.com" --include=*.py . | wc -l` → 0
- [ ] **C-11** Write `tests/test_panel.py` — `build_detail_panel(record)` renders logline, credits, category, review-status badge, and both links
  - Verify: `uv run pytest tests/test_panel.py -q` → fails (red)
- [ ] **C-12** Implement `components/panel.py::build_detail_panel(record)`; contested records show the per-source breakdown
  - Verify: `uv run pytest tests/test_panel.py -q` → passes (green)
- [ ] **C-13** Create `app.py` — Dash app, `server = app.server` for gunicorn, dark theme, `dcc.Location` for routing
  - Verify: `uv run python -c "import app; print(type(app.server))"` → a Flask object
- [ ] **C-14** Implement the app layout: header, season chart, filter chips, episode table, detail panel container
  - Verify: `uv run python app.py` starts; `curl -s localhost:8050 | grep -c "spooky"` → at least 1
- [ ] **C-15** Implement the chart-click callback — clicking a segment filters the table to that season + category; clicking a season label filters to the whole season
  - Verify: run locally, click the Mythology segment of season 5, confirm the table shows only those episodes. Paste the row count.
- [ ] **C-16** Implement the row-click callback opening the detail panel
  - Verify: run locally, click a row, confirm panel shows logline + both links
- [ ] **C-17** Implement URL sync — season, category, sort, text filter, and selected episode read from and write to the URL
  - Verify: load `/season/5?category=mythology`, confirm the filter is pre-applied on first paint
- [ ] **C-18** Add the footer with the verbatim attribution text from PRD §11.2, including the TMDB clause
  - Verify: `curl -s localhost:8050 | grep -c "unofficial fan project"` → at least 1
- [ ] **C-19** Deploy to Railway, always-on. **Sleep/serverless must be OFF** (PRD §4.1).
  - Verify: `curl -s -o /dev/null -w "%{http_code}" https://spooky.evanappel.me` → 200. Wait 15 minutes idle, repeat — still 200, not 502.
- [ ] **C-20** ⚡ **VERTICAL SLICE COMPLETE** — chart → click → table → panel → out-links, live on the real domain with 12 records.
  - Verify: `uv run pytest -m "not network" -q` green; `uv run ruff check .` clean; `uv run ty check` clean; site loads. Paste all four outputs.

---

## Group D — Ingest Pipeline
> Depends on: A-01…A-05, B-01…B-08. Runs in parallel with Group C.
> Read PRD §8.1 before writing any fetcher — each step has a documented landmine.

- [ ] **D-01** Implement `build/01_spine.py` — `GET https://api.tvmaze.com/shows/430/episodes`, no key, **no `specials=1`**, writes `data/raw/tvmaze_episodes.json`
  - Verify: `uv run pytest tests/test_spine.py -q` → green
- [ ] **D-02** Add `@pytest.mark.network` test hitting the live TVmaze endpoint, asserting 218 records
  - Verify: `uv run pytest -m network tests/test_spine.py -q` → passes
- [ ] **D-03** Implement a shared `build/_http.py` client — descriptive User-Agent from `WIKI_USER_AGENT`, ~1 req/sec throttle, explicit retry with backoff. **Never swallow an exception** (CLAUDE.md).
  - Verify: `uv run pytest tests/test_http.py -q` → green; confirm a 429 raises rather than returning None
- [ ] **D-04** Implement the brace-balanced template extractor in `build/wikitext.py`. **Not a regex** — a regex drops all 16 S10/S11 rows.
  - Verify: `uv run pytest tests/test_wikipedia.py -q -k balanced` → green, 16 rows from the S10 fixture
- [ ] **D-05** Implement case-insensitive dagger detection on `RTitle` matching `/double[- ]dagger/i`
  - Verify: `uv run pytest tests/test_wikipedia.py -q -k dagger` → green
- [ ] **D-06** Implement `<hr>` multi-value splitting for director/writer fields
  - Verify: `uv run pytest tests/test_wikipedia.py -q -k split` → green
- [ ] **D-07** Implement `build/02_wikipedia.py` — 11 **serial** requests to `action=parse&page=The X-Files season N&prop=wikitext`. **Do not parse `List_of_The_X-Files_episodes`** (transcluded; contains only film rows).
  - Verify: `uv run python build/02_wikipedia.py` writes 11 files; total extracted rows printed and re-derived, not hard-coded
- [ ] **D-08** Implement `build/03_wikidata.py` — one SPARQL query for enwiki title, IMDb ID (P345), TMDB ID. Reconcile the three "The Truth" duplicates by hand into `data/overrides/wikidata_dupes.json`.
  - Verify: `uv run python build/03_wikidata.py` → prints item count; `data/raw/wikidata.json` has no duplicate `qid`
- [ ] **D-09** Implement `build/04_labels.py` — fetch dom111 raw JSON once, **pin the blob SHA** in the script, fail loudly if the SHA no longer resolves
  - Verify: `uv run python build/04_labels.py` → 143 MOTW + 75 mythology, 0 nulls. Paste the counts.
- [ ] **D-10** Create `data/overrides/fox_dvd.json` — the Fox "Mythology" box-set episode lists, hand-entered from the four volumes, each entry citing its volume
  - Verify: `uv run python -c "import json;d=json.load(open('data/overrides/fox_dvd.json'));print(len(d))"` → count matches the volumes; every entry has a `source_volume`
- [ ] **D-11** Implement `build/05_people.py` — 218 `/guestcast` + 218 `/guestcrew` calls, throttled ~20/10s, **with an explicit retry pass**. Parse crew as the **union of Writer, Story, Teleplay**.
  - Verify: `uv run python build/05_people.py` → prints per-episode coverage; **0 episodes missing**. A naive sweep loses 10–15; if any are missing, the retry pass is broken.
- [ ] **D-12** Add a test asserting Writer-only filtering drops 11 episodes and the union drops none
  - Verify: `uv run pytest tests/test_people.py -q` → green
- [ ] **D-13** Implement `build/06_articles.py` — **one** `Special:Export` POST with all 214 titles, `curonly=1`. Record each article's revision ID.
  - Verify: `uv run python build/06_articles.py` → single request, ~4.1 MB XML, every article has a revision ID
- [ ] **D-14** Extract level-2 `Production` and `Themes` sections plus every episode→episode wikilink into `data/raw/article_sections.json`
  - Verify: `uv run pytest tests/test_articles.py -q` → green; wikilink edge count printed

---

## Group E — Merge, Classify, Emit
> Depends on: Group D complete, B-09…B-13.

- [ ] **E-01** Implement `spooky/classify.py::derive_label(fox, wiki, dom111, has_creature)` — the five rules of PRD §5.3, returning `(label_derived, contested, rationale)`
  - Verify: `uv run pytest tests/test_classify.py -q` → all green
- [ ] **E-02** Create `data/overrides/creature.json` — `has_creature` boolean per episode, AI-seeded from titles and credits, **flagged for owner review**
  - Verify: file has 220 entries; every entry has `source: "ai-seeded"` or `"human-reviewed"`
- [ ] **E-03** Implement `build/07_merge.py` — joins all sources on TVmaze `id`, applies the two-parter policy (TVmaze shape, 218 rows, Wikipedia values duplicated), special-cases the Amor Fati title join
  - Verify: `uv run pytest tests/test_merge.py -q` → green
- [ ] **E-04** Hand-enter the two film records into `data/overrides/films.json` from Wikipedia — nullable season/episode/production code; *Fight the Future* mythology, *I Want to Believe* not
  - Verify: `uv run python -c "import json;print(len(json.load(open('data/overrides/films.json'))))"` → 2
- [ ] **E-05** Implement the sacred-edits guard in `build/07_merge.py` — refuse to write `logline` when `review_status == "human-reviewed"`; emit a diff and raise instead
  - Verify: `uv run pytest tests/test_review_guard.py -q` → green
- [ ] **E-06** Implement per-field provenance — every field carries its source and license per PRD §8.2
  - Verify: `uv run pytest tests/test_provenance.py -q` → green; no field lacks a source
- [ ] **E-07** Run the full merge → `data/episodes/*.json`, 220 files, committed
  - Verify: `ls data/episodes/*.json | wc -l` → 220. Counts printed by the script must be **re-derived**, not hard-coded.
- [ ] **E-08** Implement `build/09_emit.py` — writes `data/dist/spooky-episodes.json`, `.csv`, and `spooky.sqlite` with an FTS5 table over title + logline + tags
  - Verify: `uv run python build/09_emit.py`; `sqlite3 spooky.sqlite "select count(*) from episodes"` → 220
- [ ] **E-09** Write `data/README.md` — full field dictionary, source and license per field, CC BY-SA 4.0 statement, regeneration instructions
  - Verify: every field in `data/dist/spooky-episodes.json` appears in the dictionary. Diff the key sets programmatically.
- [ ] **E-10** Add the legal-shape test to CI — no `synopsis` key, no `image` key, no logline over 30 words, no IMDb rating field
  - Verify: `uv run pytest tests/test_legal.py -q` → green
- [ ] **E-11** Print and record the **re-derived** classification counts; compare against the PRD §5.1 table and document any drift
  - Verify: paste actual counts. If mythology ≠ 70 TV episodes for Wikipedia, investigate before proceeding.

---

## Group F — Loglines & Review CLI
> Depends on: E-07. Runs in parallel with Group G.

- [ ] **F-01** Write `tests/test_loglines.py` — generated loglines are ≤30 words and contain no verbatim run of >8 words from any source text
  - Verify: `uv run pytest tests/test_loglines.py -q` → fails (red)
- [ ] **F-02** Implement `build/08_loglines.py` — drafts one logline per record via the Anthropic API from **factual inputs only** (title, credits, air date, classification, Wikipedia Production/Themes). Writes `logline_generated`, sets `review_status: "ai-drafted"`. **Never writes `logline` directly.**
  - Verify: `uv run pytest tests/test_loglines.py -q` → green
- [ ] **F-03** Write `tests/test_review_cli.py` — approve promotes to `human-reviewed` and copies `logline_generated` → `logline`; edit stores the edited text; reject sets `needs-work` with the note
  - Verify: `uv run pytest tests/test_review_cli.py -q` → fails (red)
- [ ] **F-04** Implement `tools/review.py` — walks records where `review_status != "human-reviewed"`, one at a time, showing the draft, its sources, and the episode facts; accepts approve / edit / reject-with-note; writes back to `data/episodes/*.json`
  - Verify: `uv run pytest tests/test_review_cli.py -q` → green
- [ ] **F-05** Add `--status` flag printing review progress (`147 / 220 human-reviewed`)
  - Verify: `uv run python tools/review.py --status` → prints counts
- [ ] **F-06** Add a regeneration-safety test — re-running `08_loglines.py` after review changes zero human-reviewed records
  - Verify: `uv run pytest tests/test_review_guard.py -q -k regen` → green
- [ ] **F-07** 📋 **OWNER TASK** — review all 220 loglines through the CLI
  - Verify: `uv run python tools/review.py --status` → `220 / 220 human-reviewed`
- [ ] **F-08** Surface the review-status badge in the detail panel (`AI-drafted` / `human-reviewed`)
  - Verify: `uv run pytest tests/test_panel.py -q -k badge` → green

---

## Group G — Real Data Integration
> Depends on: E-07, Group C complete.

- [ ] **G-01** Point `app.py` at `data/episodes/` instead of `data/episodes_sample/`; delete the sample directory
  - Verify: app loads 220 records; `ls data/episodes_sample 2>&1` → no such directory
- [ ] **G-02** Confirm the chart renders 11 season bars with three segments each and excludes both films
  - Verify: run locally; paste per-season segment counts and confirm they match `data/dist/spooky-episodes.csv`
- [ ] **G-03** Add the Films card — the two film records, outside the season chart
  - Verify: `uv run pytest tests/test_films.py -q` → green; both films visible in the UI
- [ ] **G-04** Add the contested filter toggle ("show contested only")
  - Verify: toggle on → row count equals the count of `label_contested == true`. Paste both numbers.
- [ ] **G-05** Verify all 220 out-links resolve — spot-check 10 episodes and both films
  - Verify: paste the 12 URLs and their HTTP status codes. Films must degrade gracefully (not on any service).
- [ ] **G-06** 📋 **OWNER TASK** — spot-check classifications against the Fox DVD volumes; adjudicate any contested episode you disagree with into `data/overrides/`
  - Verify: paste the list of episodes you changed and why

---

## Group H — Polish, A11y, Docs
> Depends on: Group G. Runs in parallel with F.

- [ ] **H-01** Apply the visual identity — dark theme, restrained modern, subtle X-Files signals. **No show imagery, no wordmark, no X-glyph** (CLAUDE.md C2). Original SVG/CSS only.
  - Verify: `grep -riE "\.(jpg|jpeg|png|webp)" --include=*.py --include=*.css . | wc -l` → 0
- [ ] **H-02** Verify the categorical palette is colorblind-safe; simulate deuteranopia and protanopia
  - Verify: paste the three hex values and the simulation result
- [ ] **H-03** Responsive layout — chart, table, and panel usable at 375px width
  - Verify: load at 375px; no horizontal body scroll; all controls reachable
- [ ] **H-04** Keyboard navigation across chart, table, and panel; visible focus states
  - Verify: tab through the whole app without a mouse; paste the focus order
- [ ] **H-05** Add the screen-reader data-table alternative to the chart
  - Verify: `uv run pytest tests/test_a11y.py -q` → green
- [ ] **H-06** Contrast audit — all text at WCAG AA
  - Verify: paste the lowest contrast ratio found and its location
- [ ] **H-07** Write `README.md` — what it is, the classification-disagreement story, data provenance, how to rebuild, licenses, screenshots-free
  - Verify: a reader with no context can state what the site does after 30 seconds
- [ ] **H-08** Add a `/about` view explaining the ternary classification and *why sources disagree*
  - Verify: page renders; names all three label sources
- [ ] **H-09** Add `spooky.svg` — original mark, **not** derived from the X-Files wordmark or X-glyph
  - Verify: confirm in writing it is original work

---

## Group I — Deploy Hardening & Scheduled Refresh
> Depends on: Group H.

- [ ] **I-01** Confirm Railway always-on; sleep/serverless disabled
  - Verify: leave idle 20 minutes, then `curl -s -o /dev/null -w "%{http_code}"` → 200, not 502. Paste the result.
- [ ] **I-02** Point `spooky.evanappel.me` at the Railway service; TLS valid
  - Verify: `curl -sI https://spooky.evanappel.me | head -1` → 200
- [ ] **I-03** Add GitHub Actions secrets: `TMDB_API_KEY`, `ANTHROPIC_API_KEY`, `WIKI_USER_AGENT`
  - Verify: `gh secret list --repo EvanWAppel/spooky` → all three present
- [ ] **I-04** Implement `.github/workflows/refresh.yml` — monthly, re-runs `01`–`07`, opens a PR with the data diff
  - Verify: `gh workflow run refresh.yml` → opens a PR
- [ ] **I-05** Add the refresh guard test — the job **fails loudly** if it would modify any `human-reviewed` field
  - Verify: `uv run pytest tests/test_review_guard.py -q -k refresh` → green. Do not let it skip silently (CLAUDE.md).
- [ ] **I-06** Set `status = "live"` for spooky in `../projects.toml`
  - Verify: `grep -A2 'projects.spooky' ../projects.toml | grep status` → `live`

---

## Group J — v1 Acceptance (the Check phase)
> Depends on: all groups. **This is the human's responsibility.**

- [ ] **J-01** All 220 records present; every count re-derived at build time, none hard-coded
  - Verify: `grep -rnE "\b(218|220|71|143|75)\b" build/ --include=*.py` → only in comments or assertions, never as logic
- [ ] **J-02** `uv run pytest -m "not network"` fully green
  - Verify: paste the summary line
- [ ] **J-03** `uv run ruff check .` and `uv run ty check` both clean
  - Verify: paste both outputs
- [ ] **J-04** `uv run prek run --all-files` clean
  - Verify: paste the output
- [ ] **J-05** All 220 loglines `human-reviewed`
  - Verify: `uv run python tools/review.py --status` → `220 / 220`
- [ ] **J-06** Footer attribution present and **verbatim** per PRD §11.2, including the TMDB clause
  - Verify: diff the rendered footer against PRD §11.2 character by character
- [ ] **J-07** Published dataset + `data/README.md` field dictionary accurate
  - Verify: key sets match programmatically; paste the diff (must be empty)
- [ ] **J-08** No 502 on a cold first request
  - Verify: idle 20 minutes, then load in a fresh browser profile. Paste the status code.
- [ ] **J-09** 📋 **OWNER TASK — recruiter legibility.** Show it to someone who has never seen *The X-Files*. Ask what it does. Ten seconds.
  - Verify: write down what they actually said, verbatim, in POSTMORTEM.md
- [ ] **J-10** 📋 **OWNER TASK** — confirm no constraint C1–C7 is violated anywhere in the shipped site
  - Verify: walk the C1–C7 list against the live site and initial each

---

## Deferred — do not build in v1

Specified in PRD §7. Listed here so no agent starts them by accident.

- [ ] **V2-01** Viewership charts — **gated on hand-QA**, every source claim failed verification
- [ ] **V2-02** Keyword playlists — in-app queue, URL-encoded, CSV/Markdown export
- [ ] **V2-03** Layered search — curated tags → FTS5 → semantic embeddings
- [ ] **V2-04** Trivia writeups — **Wikipedia only**, never Fandom or IMDb
- [ ] **V2-05** 100% stacked chart toggle
- [ ] **V3-01** People profiles — 343 recurring actors
- [ ] **V3-02** Episode interconnection graph from ~1,217 Wikipedia wikilinks
- [ ] **V3-03** Connections to outside works
- [ ] **V3-04** Static-site migration if SEO matters
- [ ] **XX-01** ~~Video extras~~ — **dropped**, all claims failed verification
- [ ] **XX-02** ~~Contemporary review sentiment~~ — **unassessed**; research agent errored. Redo the research before deciding.
