# spooky — Handoff

> Cold-start context for a different agent, a different model, or Evan in three
> months. Written 2026-07-26 at the end of the RECL **Requirements** phase;
> **updated 2026-07-27** — the Execute phase has begun and Group A is complete.

## Read these, in this order

1. **`CLAUDE.md`** — standing rules. The "Project-specific rules" section is
   legal constraints, not style. Violating them is a real problem.
2. **`PRD.md`** — the full spec. §2 (constraints), §5 (classification), §8
   (pipeline landmines), and §13 (known unknowns) are the load-bearing sections.
3. **`TASKS.md`** — the execution plan. Groups A and C-01…C-18 are done and
   verified; next up are **Group B/D** (the ingest pipeline) and **C-19** (deploy).
4. **`DECISIONS.md`** — the decision register: who decided what, what else was
   considered, and which calls Claude made on Evan's behalf. §D's blocking
   items are all resolved as of 2026-07-27; OPEN-03 and OPEN-04 remain open
   but block nothing.
5. This file — the *why* behind decisions that look arbitrary.

## The 60-second version

`spooky` is a public X-Files episode data explorer and a portfolio piece. The
headline chart shows mythology vs. monster-of-the-week vs. standalone episodes
per season; clicking a bar segment filters a sortable table; clicking a row opens
a detail panel with a logline, credits, and out-links to IMDb and TMDB.

220 records (218 episodes + 2 films). Python/Dash on Railway, always-on. Data is
built offline by a committed pipeline and never fetched at request time.

## Non-obvious decisions and why

**Why not IMDb ratings, when the user asked for them?** IMDb's non-commercial
license bars republication into any online database, and OMDb holds no license to
sublicense it. The licensed bulk product is $50,000/yr. We ship TVmaze
`rating.average` and *link* to IMDb pages — linking is unrestricted.

**Why not a Hulu button, when the user asked for one and has an account?**
Hulu's ToS bars scraping *and* unauthorized linking, there are no public
per-episode URLs, and Disney is folding Hulu into Disney+ in late 2026. We link
to the TMDB season watch page instead: sanctioned, provider-agnostic,
auto-updating.

**Why pay ~$5/mo for always-on instead of free?** Railway sleeps after ~10
minutes and the first request to a slept service can return 502 — landing on
exactly the recruiter this site exists to impress.

**Why three categories instead of two?** Four sources give four mythology counts
(≈60 / 70 / 71 / ≈80) and disagree on ~22 episodes. Rather than pick one and
defend it, we store all three source labels and render the disagreement. This is
the most interesting thing on the site — treat it as a feature, not a caveat.

**Why loglines instead of synopses?** No lawful source of episode synopses exists
for public republication. Every source is CC BY-SA (share-alike attaches) or
non-commercial, and *Twin Peaks Productions v. Publications International* held
detailed plot recounting non-transformative. A ≤30-word original logline is far
short of that line.

**Why no images at all?** No source gives a clean per-image license for public
use, and the wordmark/X-glyph is a live trademark (USPTO Reg. 5555723). This is
risk management, not settled law — §107 fair use has protected screenshots — but
it's the right posture for a public site, and it forces a more interesting
visual design.

**Why JSON files as source of truth with SQLite as a build output?** The owner
reviews and edits AI-drafted loglines. `git diff` on a binary SQLite file shows
nothing. Readable diffs are the whole point; SQLite is regenerable.

**Why is "edits are sacred" enforced by a test?** A monthly refresh job that
silently overwrites human-reviewed prose would destroy hours of work invisibly.
The guard raises rather than skipping (CLAUDE.md: *do not hide or wrap errors*).

## Landmines that will silently corrupt the data

These were found by adversarial verification. Each fails **quietly**.

| Landmine | Consequence |
|---|---|
| `?specials=1` on the TVmaze episodes call | 222 records instead of 218 |
| Regex instead of a brace-balanced wikitext parser | All 16 season 10–11 rows vanish |
| Case-sensitive `double dagger` match | 7 season-3 episodes lose their flag |
| Matching the dagger on `Title` instead of `RTitle` | Flags missed |
| Parsing `List_of_The_X-Files_episodes` | Transcluded — you get only the 2 film rows |
| Filtering crew on `guestCrewType == "Writer"` | 11 episodes lose writers; use Writer ∪ Story ∪ Teleplay |
| No retry pass on the 436 people calls | 10–15 episodes silently lose cast |
| 214 individual `action=parse` calls | Half return 429; use one `Special:Export` POST |
| Joining on title without the Amor Fati special case | Spurious miss |
| Hard-coding 218 / 220 / 71 / 143 | Upstream tables shift; re-derive at build time |

## Corrected claims — do not reintroduce

Adversarial verifiers refuted these. The corrected version is what's true.

- Wikipedia has **71 daggered rows = 70 TV episodes + 1 film** (not "70 rows = 71 episodes").
- Pluto TV has **no** public unauthenticated API — it returns 401 and needs a JWT.
- IMDb's bulk ratings product is **$50,000/yr**, not $150,000.
- There are **343** recurring actors, not 345; names and person_ids are equivalent here.
- TMDB **does** support per-episode producer credits — coverage is just sparse.
  TMDB's series-level `episode_count` is wrong (Glen Morgan: 218 listed vs 16 actual).
- *Feist* does not make facts unconditionally free — the rule turns on **selection
  and arrangement**, and a contract accepted to obtain data binds regardless of
  copyright.

## What we do NOT know

The feasibility study lost 13 of 57 agents to network errors. These areas are
**unassessed, not cleared**:

- **All viewership claims failed verification** — hence viewership is v2, gated
  on full hand-QA of the Wikipedia column.
- **All video-extras claims failed verification** — hence the feature is dropped.
- **Contemporary review sentiment research produced nothing** — that agent
  errored outright. Redo the research before designing this feature.
- The Wikipedia 217-row parse and its field-population rates were never
  independently confirmed. Re-derive and count.

## State of the world right now

*Verified against disk 2026-07-27.*

**Done — Groups A and C-01…C-18 verified, 31 of 123 tasks.**

- Branch **`init-scaffold`**, remote `github.com/EvanWAppel/spooky.git`. Do not
  push to `main`. Commits: *Initialize spooky scaffold*, *Vertical slice…*.
- The vertical slice **works and was verified in a live browser**: chart-click
  → season+category filter, row-click → detail panel, URL routing pre-applies
  on first paint. 29 tests passing, ruff/ty clean, prek hooks green.
- `tests/conftest.py` exists (app-layer fixtures: `sample_data_dir`,
  `episodes_df`, `contested_record`, `render_text`); suite passes from any cwd.
- `spooky/values.py` holds the null-handling layer — **read its docstring
  before writing any pipeline code.** JSON `null` arrives as `NaN`/`pd.NA`
  through pandas, never `None`; three bugs came from that this session.

**Open — C-19/C-20:** deploy to Railway (always-on approved — the account
already hosts mccoy), then the Group C gate.

**Not started**

- `build/` and `tools/` are **empty**. The entire ingest pipeline (Groups D–G)
  is unwritten. Module names are `build/spine.py` … `build/emit.py` with run
  order in `build/__main__.py` (task D-15) — **not** the old `01_`-prefixed
  names, which tests cannot import.
- No real data — everything runs on the 12 sample records.

**Rulings already made — do not re-open** (full detail in `DECISIONS.md` §D):

- **Classification nulls abstain** (OPEN-01). PRD §5.3 is vote-based; films
  carry one Wikipedia vote; <3 votes ⇒ contested; zero votes ⇒ build fails.
- **Railway always-on approved** (OPEN-02).
- **The 175-finding review batch is retired** (OPEN-05). Confirmed items are
  fixed; do not re-litigate the rest.

**API keys needed:** **TMDB** and **Anthropic**. OMDb and YouTube are *not*
needed — don't let anyone re-add them. Note that no task yet creates a populated
local `.env`; only `.env.example` exists — Group F (loglines) will stall on the
Anthropic key without an owner step.

## Ground rules for whoever continues

- **CLAUDE.md prime directive: don't do anything you're unclear about — ask.**
- Execute prompt is *"Work on the next tasks. Check them off as completed. Stop
  if you have questions."*
- TDD: write the failing test first. Group B is deliberately all red.
- Do not push to `main`.
- Every task has a `Verify:` line. Run it and paste real output — the Check phase
  belongs to the human, so leave evidence.
- If you find yourself repeating a correction, update `CLAUDE.md` (that's the
  Loop step).
