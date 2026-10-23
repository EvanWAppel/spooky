# spooky — Primer

## Next session — 2026-10-24 weekend

**Goal (2 lines).** A public, always-on *X-Files* episode data explorer (Dash + Flask SSR on
Railway) whose headline feature is that sources disagree on which episodes are "mythology":
three verdicts per episode, a voted label, and the disagreement shown openly.

**You are unattended.** Work in the worktree on branch `weekend-2026-10-24`, never in
`~/Documents/portfolio/spooky` (Evan's checkout, on `feat/fts5-search`). Open a PR when done;
**never merge, never deploy, never push to `main`.** Prime directive (CLAUDE.md): if anything
is unclear, stop and write the question into `BLOCKED.md` instead of guessing.

### Current state (checked 2026-10-22)

- `main` @ `427eb99` — v1 code complete + Group UI + Group T (taglines, minus T-06/T-13) +
  Group R (FTS5 search, provenance dashboard, SSR/SEO pages). No open PRs.
- Default-branch checks: `uv run pytest -m "not network" -q` → **295 passed, 1 skipped,
  1 deselected, 10 warnings** (warnings = Dash `DataTable` deprecation). `ruff check`,
  `ty check`, `prek run --all-files` all clean.
- **Live:** `https://spooky.evanappel.me/` → 200 over TLS (Railway, `server: railway-hikari`);
  `/sitemap.xml` → 200; `/episode/s03e15` serves "Piper Maru" in raw HTML. The Railway origin
  `https://web-production-61a00.up.railway.app/` also → 200. `BLOCKED.md` and TASKS.md
  (C-19, I-02, R-13) still describe the deploy as pending — they are stale.
- **Unmerged in-flight work:** `origin/feat/fts5-search` carries WIP commit `e6f6f70`
  (2026-10-17 backup sweep) on top of `fa692a2`. It holds **Evan's finished logline review —
  all 220 records `human-reviewed`** (main has 1), plus `AGENTS.md`, the ROCRLL block in
  `CLAUDE.md`, D-29 marked accepted in `DECISIONS.md`, and refreshed `BLOCKED.md` items.
  None of those paths changed on `main` since `fa692a2`, so they port cleanly. The WIP
  commit's diffs to `tools/review.py` / `tests/test_review_cli.py` are just "before T-07":
  **do not take them.**

### Autonomous tasks, in order

1. **W-01 Port the reviewed loglines + docs from `e6f6f70` (M).**
   `git checkout e6f6f70 -- AGENTS.md CLAUDE.md DECISIONS.md data/episodes`, then hand-merge
   `BLOCKED.md`: take the WIP's reworded deploy/R-13 items, drop the D-29 item (accepted),
   **keep every item this branch added**. Copy the files verbatim and don't edit any
   episode JSON: human-reviewed content is sacred. Don't touch `tools/` or `tests/`.
   - Done: `uv run python tools/review.py --status` → `220 / 220` loglines;
     `git diff origin/main --stat -- tools tests` is empty; full suite green. Paste the
     output under J-05 in TASKS.md. Leave the box unticked: F-07 and J-05 are Evan's to tick.
2. **W-02 Record deploy evidence + de-stale docs (S).** Paste real `curl` output under
   C-19, I-02 and R-13 in TASKS.md (domain 200 + TLS; SSR text in raw HTML; sitemap/robots
   resolve). Fill the README **Live demo** line with `https://spooky.evanappel.me`. Add a
   one-line "deployed" status to `docs/deploy.md`. Only tick boxes whose Verify line you
   actually ran. Leave R-13's Search Console submission and every 📋 OWNER box unticked.
   - Done: `grep -n "Live demo" README.md` shows the URL; `uv run prek run --all-files` clean.
3. **W-03 Always-on check, I-01 / J-08 (S).** Don't send any request for ≥20 min (use
   `Monitor`/a background `sleep 1260 && curl …`), then
   `curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://spooky.evanappel.me/`.
   Paste the result under I-01 and J-08. You can't rule out other traffic, so say so. Tick
   I-01 only if the result is 200. J-08 says "fresh browser profile": record the curl
   evidence and leave the box for Evan.
   - Done: evidence pasted, with the caveat noted.
4. **W-04 Refresh `HANDOFF.md` (S).** It still says "Execute phase has begun, Group A
   complete" (2026-07-27). Rewrite the status and "read these" sections to match today.
   Keep the "non-obvious decisions" content, which is still true.
   - Done: no claim in HANDOFF.md contradicts TASKS.md; prek clean.
5. **W-05 XX-02 research memo (M, optional, last).** The "contemporary review sentiment"
   research errored and was never redone. Write `docs/research/xx-02-review-sentiment.md`
   covering candidate sources, their licences, whether quoting or scoring is lawful under
   CLAUDE.md, and a recommendation. **Research only. Build nothing, add no deps, and never
   touch Fandom, TV Tropes, IMDb, Pluto TV or insidethex.co.uk.** Mark XX-02 "researched,
   awaiting decision"; Evan decides.
   - Done: memo exists, cites sources with URLs, ends in a recommendation + open questions.

Finish: run the full Check once (`uv run pytest -m "not network" -q && uv run ruff check . &&
uv run ty check && uv run prek run --all-files`). Do an independent fresh-context review of
the diff (ROCRLL), then `git push -u origin weekend-2026-10-24` and `gh pr create` with the
evidence in the body. Put the PR link last in your report.

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
- Flipping `verified = true` in `project.toml`: that is Evan's/the project session's call.
