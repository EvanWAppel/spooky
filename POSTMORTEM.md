# spooky — Process Postmortem

> A living document. Each phase appends a dated section. This is the **Loop**
> step of RECL (Requirements → Execute → Check → Loop) made explicit.

---

## 2026-07-26 — Requirements phase

**What was attempted:** the entire RECL Requirements phase in one session — PRD,
CLAUDE.md, and TASKS.md — for a project that had never existed before. Three
things were being evaluated simultaneously alongside the work itself: the desktop
Claude Code app on a large project, Opus 5 + Ultracode, and auto-mode.

### What actually happened

| | |
|---|---|
| Interview rounds | 9 (36 structured decisions) |
| Feasibility research | 57 agents, ~3.1M tokens, 1,321 tool calls, ~49 min |
| Research agents lost to network errors | **13 of 57** |
| Decisions overturned by research **after** being agreed | **4** |
| Requirements review | 8 dimensions, adversarially verified |
| Artifacts produced | PRD.md, CLAUDE.md, TASKS.md, HANDOFF.md, POSTMORTEM.md |
| Tasks defined | ~110 across 10 groups, every one with a Verify line |
| Lines of code written | **0** |

### The four overturned decisions

This is the headline result. Each had been decided in the interview and was
invalidated by research *before* any code existed:

1. **IMDb ratings** — agreed as the one v1 feature beyond the vertical slice.
   IMDb's non-commercial license bars republication into any online database, and
   OMDb cannot sublicense it. → TVmaze ratings, IMDb links only.
2. **"Open in Hulu"** — in the opening sentence of the original brief. Hulu's ToS
   bars scraping *and* unauthorized linking; no public per-episode URLs; Hulu
   folds into Disney+ late 2026. → TMDB season watch pages.
3. **Dash on Railway (default sleep)** — Railway sleeps after ~10 min and can 502
   on the first request, hitting exactly the recruiter the site exists for.
   → always-on, ~$5/mo.
4. **Episode synopses in the detail panel** — no lawful source exists for public
   republication, 0 of 220. → original ≤30-word loglines, AI-drafted and
   human-reviewed.

A fifth was substantially revised: the "official Fox box sets" classification
authority turned out to cover only ~60 episodes, predate the revival by a decade,
and omit "Musings of a Cigarette Smoking Man" — with four sources disagreeing on
~22 episodes. That became the ternary + per-source-badge design, which is now
arguably the most interesting thing in the product.

### Verdicts

**RECL Requirements in one go — better than expected.** The interview surfaced
decisions that wouldn't have come up otherwise, and front-loading feasibility
research into Requirements caught four real problems before any code existed.
Worth repeating.

**Desktop Claude Code app — good fit.** Handled a long, artifact-heavy session
with background work well. Caveat: Requirements is mostly conversation; the
harder test is the Execute phase with heavy file editing and test runs.

**Opus 5 + Ultracode — clearly worth it.** The research run overturned four
already-made decisions. Discovering the IMDb licensing problem in week three
instead of hour one would have cost far more than the tokens did.

**Auto-mode — worked well, with one real incident.** Its safety classifier went
down mid-session (`claude-sonnet-5 is temporarily unavailable, so auto mode
cannot determine the safety of Bash`), blocking Bash while read-only tools kept
working. Recovered on its own within a few minutes. Worth knowing that a
classifier outage degrades a long working session rather than failing cleanly.

### What went well

- **Research ran concurrently with the interview.** The 49-minute study happened
  in the background while questions that only the owner could answer were being
  asked. Almost no wall-clock was spent waiting.
- **Adversarial verification earned its keep.** Verifiers refuted several
  confident-sounding claims, including a 3× error in IMDb's licensing cost, a
  "public API" that returns 401, and a recurring-actor count. Single-pass research
  would have shipped all of them into the PRD as fact.
- **Reading the actual process source mattered.** Fetching `agent_programming.pdf`
  and `aiprompts/` from the pycon2025 repo — rather than inferring RECL from the
  acronym — changed how TASKS.md was written. The Execute prompt says *"Stop if
  you have questions,"* so TASKS.md was written to a self-sufficiency bar it
  otherwise wouldn't have met.

### What didn't

- **13 of 57 research agents died on network errors.** Contemporary review
  sentiment analysis produced *nothing* and is recorded as unassessed rather than
  rejected. All viewership claims and all video-extras claims failed
  verification. Real coverage gaps, carried forward in PRD §13 instead of being
  papered over — but gaps nonetheless.
- **The scope grew during the interview and then had to be cut back.** The v1
  list was tight, then loglines pulled the review CLI into v1, then viewership
  went out. A cleaner interview would have sequenced the release plan once,
  at the end, rather than incrementally.
- **One answer conflicted with another** (viewership deferred, then "ship all of
  it" on a list containing viewership). Resolved by taking the more specific
  answer, and flagged rather than silently chosen — but the question design
  caused it.
- **A transcription error made it into CLAUDE.md** — two lines of the dictated
  prime directive got merged ("use uv" / "run python tools with uv run python").
  Caught only by comparing against the canonical `agents.md` in the pycon2025
  repo. Dictated text should be diffed against its source, not trusted.

### Open questions for the next phase

- Does a PRD written this thoroughly actually survive contact with the Execute
  phase, or does it get contradicted in week one? **This is the real test of
  whether the requirements were any good**, and it can only be answered later.
- Was ~110 tasks the right granularity, or will they prove too fine or too coarse?
- Do the Verify lines actually get run, or do they become decoration?
- Does the "edits are sacred" design survive the first scheduled-refresh PR?

---

## Template for future entries

```
## YYYY-MM-DD — <phase> phase

### What was attempted
### What actually happened  (numbers, not impressions)
### What went well
### What didn't
### What changed in CLAUDE.md as a result   ← the Loop step
### Open questions for the next phase
```
