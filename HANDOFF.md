# spooky — Handoff

> Cold-start context for a different agent, a different model, or Evan in three
> months. First written 2026-07-26 at the end of the Requirements phase;
> **refreshed 2026-10-22** (weekend branch `weekend-2026-10-24`, W-04). v1 code
> is complete and **live at <https://spooky.evanappel.me>**; what remains is
> owner checks (the Check phase) plus a few gated items. `TASKS.md` is the
> source of truth for task status. If this file disagrees with it, `TASKS.md` wins.

## Read these, in this order

1. **`CLAUDE.md`** — standing rules (and `AGENTS.md`, its agent-neutral
   pointer). The "Project-specific rules" section is legal constraints, not
   style. Violating them is a real problem. The ROCRLL block governs how work
   is orchestrated, checked and reviewed.
2. **`PRD.md`** — the full spec. §2 (constraints), §5 (classification), §7 (v2
   groups T and R), §8 (pipeline landmines), and §13 (known unknowns) are the
   load-bearing sections.
3. **`TASKS.md`** — the execution plan, with real Verify output pasted under each
   item. Groups A–I, UI, T and R are built. The remaining open boxes (owner
   checks, C-20, I-06, T-06, R-13's Search Console step) are listed under
   *State of the world* below.
4. **`BLOCKED.md`** — everything waiting on Evan, each item with exact unblock steps.
5. **`DECISIONS.md`** — the decision register: who decided what, what else was
   considered, and which calls Claude made on Evan's behalf. OPEN-01, -02 and
   -05 are resolved; D-29 (in-memory search) and D-30 (Flask SSR) are accepted.
   OPEN-03 and OPEN-04 remain open but block nothing.
6. **`docs/deploy.md`** (Railway setup) and **`docs/ai-pipeline.md`** (the
   Anthropic-backed logline steps).
7. This file — the *why* behind decisions that look arbitrary.

## The 60-second version

`spooky` is a public X-Files episode data explorer and a portfolio piece. The
headline chart stacks one block per episode per season, colored mythology vs.
monster-of-the-week vs. standalone. Clicking a block opens that season's list
with the episode selected, and the episode information below the list shows a
logline, credits, the per-source classification split, and out-links to IMDb
and TMDB. Around that: site-wide FTS5 search (`?text=`), a `/taglines`
catalogue of the opening-title variants, a `/provenance` dashboard, and
server-rendered crawlable pages (`/episode/<id>`, `/seasons/<n>`,
`sitemap.xml`) for SEO.

220 records (218 episodes + 2 films). Python/Dash + Flask on Railway, always-on.
Data is built offline by a committed pipeline and never fetched at request
time. The deployed app reads no API keys.

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
- **Contemporary review sentiment** — the original agent errored; the research
  was redone 2026-10-22 (`docs/research/xx-02-review-sentiment.md`). Researched,
  awaiting Evan's decision (TASKS XX-02).
- The Wikipedia 217-row parse and its field-population rates were never
  independently confirmed. Re-derive and count.

## State of the world right now

*Verified against disk 2026-10-22 (W-04). Re-derive task counts with
`grep -c "^- \[x\]" TASKS.md` rather than trusting a number here.*

**Built and verified.** Groups A–I, UI, T and R, apart from the open boxes
listed below. The full pipeline (`build/` spine → emit, run via
`uv run python -m build`) has produced all 220 `data/episodes/*.json`, and the
monthly `refresh.yml` workflow opens a PR with any data diff. On `main`
(`427eb99`), `uv run pytest -m "not network" -q` is green (the 10 warnings are
Dash `DataTable` deprecations; that migration is a deferred design call), and
ruff, ty and prek are clean.

**Live.** `https://spooky.evanappel.me/` returns 200 over valid TLS (Railway).
SSR episode text is present in the raw HTML, and `robots.txt` and `sitemap.xml`
resolve. A 21-minute-idle curl returned 200. Evidence is pasted under C-19, I-01,
I-02, R-13 and J-08 in `TASKS.md`. Railway's sleep setting itself has not been
inspected; that confirmation is in `BLOCKED.md`.

**Loglines.** Evan's review is finished: `uv run python tools/review.py --status`
→ `220 / 220 human-reviewed`. It was ported from WIP commit `e6f6f70` onto the
weekend branch (W-01). F-07 and J-05 stay unticked until Evan ticks them. The 15
variant tagline notes are `0 / 15` because T-06 (drafting them) needs the
Anthropic key.

**Branches.** `main` is the deploy branch: Railway deploys from it, so **a merge
is a deploy**. Weekend work (W-01…W-05) is on `weekend-2026-10-24`, for a PR.
Evan's own checkout sits on `feat/fts5-search` (WIP `e6f6f70`); leave it alone.

**Still open** (see `TASKS.md` for Verify lines, `BLOCKED.md` for unblock steps):

- **Owner tasks (📋):** F-07 logline review (done in data, box unticked),
  G-06 classification spot-check, J-09 recruiter legibility, J-10 C1–C7 walk,
  T-13 tagline-gloss review, R-13 Search Console submission.
- **Check-phase boxes:** C-19 / I-01 (always-on; curl evidence in, Railway sleep
  setting unconfirmed), C-20 (vertical-slice gate), J-05 (220/220, Evan to
  tick), J-08 (curl evidence in; the fresh-browser-profile load is Evan's).
- **Gated:** T-06 tagline glosses (needs a scoped, capped `ANTHROPIC_API_KEY`;
  see the key item in `BLOCKED.md`). I-06 edits `../projects.toml`, outside this repo.
- **Deferred:** V2/V3 items; XX-02 review sentiment (researched, awaiting
  Evan's decision; see `docs/research/xx-02-review-sentiment.md`).

**Rulings already made — do not re-open** (full detail in `DECISIONS.md`):

- **Classification nulls abstain** (OPEN-01). PRD §5.3 is vote-based; films
  carry one Wikipedia vote; <3 votes ⇒ contested; zero votes ⇒ build fails.
- **Railway always-on approved** (OPEN-02).
- **The 175-finding review batch is retired** (OPEN-05). Confirmed items are
  fixed; do not re-litigate the rest.
- **Search index is built in memory from JSON** (D-29), not from the committed
  SQLite. **SEO is Flask SSR pages alongside Dash** (D-30), not a static-site rewrite.

**API keys.** Only **Anthropic**, and only for the local logline/triage/gloss
steps (`build/loglines.py`, `build/rewrite.py`, `tools/triage.py`). The running
app and the refresh workflow need no keys. TMDB, OMDb and YouTube keys are *not*
needed; don't let anyone add them. Whether the local Anthropic key is a scoped,
capped workspace key is still an open question in `BLOCKED.md`.

## Ground rules for whoever continues

- **CLAUDE.md prime directive: don't do anything you're unclear about — ask.**
- Execute prompt is *"Work on the next tasks. Check them off as completed. Stop
  if you have questions."* Never tick a 📋 OWNER box on Evan's behalf.
- TDD: write the failing test first.
- Do not push to or merge into `main`. A merge deploys.
- Every task has a `Verify:` line. Run it and paste real output — the Check phase
  belongs to the human, so leave evidence.
- If you find yourself repeating a correction, update `CLAUDE.md` (that's the
  Loop step).
