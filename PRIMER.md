# spooky — Primer

## Next session — 2026-10-24 weekend

**Goal (2 lines).** A public, always-on *X-Files* episode data explorer (Dash + Flask SSR on
Railway) whose headline feature is that sources disagree on which episodes are "mythology":
three verdicts per episode, a voted label, and the disagreement shown openly.

**You are unattended.** Work on a feature branch cut from `origin/main` (the `weekend-2026-10-24`
branch merged as PR #8), never in `~/Documents/portfolio/spooky` (Evan's checkout). Open a PR when done;
**never merge, never deploy, never push to `main`.** Prime directive (CLAUDE.md): if anything
is unclear, stop and write the question into `BLOCKED.md` instead of guessing.

### Current state (checked 2026-10-24)

- `main` @ `e0be3e5` (2026-10-23) — v1 code complete + Group UI + Group T (taglines, minus T-06/T-13) +
  Group R (FTS5 search, provenance dashboard, SSR/SEO pages). The weekend batch W-01..W-05 merged
  as PR #8: Evan's logline review ported from `e6f6f70` (220/220 `human-reviewed`, plus
  `AGENTS.md`, the ROCRLL block in `CLAUDE.md`, D-29 accepted), live-deploy curl evidence under
  C-19/I-02/R-13 and the README **Live demo** URL, the 21-minute idle check under I-01/J-08,
  the refreshed `HANDOFF.md`, and the XX-02 research memo
  (`docs/research/xx-02-review-sentiment.md`, "researched, awaiting decision"). PR #9 synced the
  blocker protocol. No open PRs.
- Default-branch checks, re-run 2026-10-24 on a fresh clone: `uv run pytest -m "not network" -q` →
  **296 passed, 1 skipped, 1 deselected, 10 warnings** (warnings = Dash `DataTable` deprecation).
  `ruff check` and `ty check` clean (`prek` not re-run).
- **Live:** `https://spooky.evanappel.me/` (I-02 ticked). C-19 and I-01 stay unticked until Evan
  confirms App Sleeping is off in Railway; J-05/F-07 wait on Evan to confirm the ported review.
- `origin/feat/fts5-search` still exists with WIP commit `e6f6f70`; its useful content is now on
  main. Leave the branch alone.

### Autonomous tasks, in order

**None left.** W-01..W-05 all merged in PR #8. What remains is Evan's, and every item is in
`BLOCKED.md`: the scoped `ANTHROPIC_API_KEY` and `[keys]` facts, the Railway always-on setting
(C-19/I-01), ticking F-07/J-05, G-06, J-09, the R-13 Search Console submission, branch
protection on `main`, and the XX-02 build/decline call. If nothing new has been added to
TASKS.md or BLOCKED.md, stop.

Before any PR, run the full Check (`uv run pytest -m "not network" -q && uv run ruff check . &&
uv run ty check && uv run prek run --all-files`), do an independent fresh-context review of the
diff (ROCRLL), and put the PR link last in your report.

### House rules that bite (from CLAUDE.md)

- `uv` for everything; `uv add` / `uv add --dev` only, never hand-edit deps in `pyproject.toml`.
- TDD with pytest; shared fixtures in `conftest.py`; ruff + ty + prek must be clean.
- Use `logging`; never hide or wrap errors; no silent skips.
- `data/episodes/*.json` is truth and the SQLite is a build output: never edit it or commit it.
  **Never overwrite a `human-reviewed` field.**
- Don't hard-code counts (218/220/71…); re-derive them.
- Legal (non-negotiable): no IMDb ratings, no show imagery/wordmark/X-glyph, no verbatim
  synopses (loglines ≤30 words), no scraping or LLM-feeding Fandom/TV Tropes/IMDb/Pluto
  TV/insidethex, no transcripts, never write "no copyright infringement intended".
- Network tests are `@pytest.mark.network`; parser tests run offline on `tests/fixtures/`.
- Every TASKS.md item has a Verify line. Run it and paste the real output.

### Do NOT do

- **Deploy, or change Railway/DNS/env vars.** Railway deploys from `main`, so a merge is a
  deploy: never merge.
- **T-06** (AI tagline glosses) and any logline re-generation or triage: these need
  `ANTHROPIC_API_KEY`, a paid key. Don't run `build/loglines.py`, `build/rewrite.py` or
  `tools/triage.py`.
- **Owner tasks:** F-07, G-06, J-09, J-10, T-13, the R-13 Search Console submission. Also
  ticking owner boxes on Evan's behalf.
- **I-06:** it edits `../projects.toml`, which is outside this repo.
- **The Dash `DataTable` → `dash-ag-grid` migration** (the 10 test warnings). It adds a
  dependency and changes the UI, it needs a browser check, and it is a design call. Don't
  silence the warnings either.
- **V2/V3 deferred items**, browser automation, reading any `.env*` file, and touching
  `~/Documents/portfolio/spooky` or the `feat/fts5-search` branch itself.
- **XX-02 build:** research is done; build nothing until Evan picks an option.
- Flipping `verified = true` in `project.toml`: that is Evan's/the project session's call.
