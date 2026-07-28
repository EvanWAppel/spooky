# spooky — Decision Register

> Every decision behind this project, with **who made it**, what else was on the
> table, and what would justify reversing it.
>
> `PRD.md` records *what* was decided. This file records *why*, *by whom*, and
> *how much to trust it* — so the decisions can be audited later instead of
> being re-litigated from memory.
>
> Created 2026-07-27, at Evan's request: *"I'm going to go with your
> recommendations, but I want you to document them so I can review them later."*

## How to read the Owner column

| Marker | Meaning |
|---|---|
| **EVAN** | Evan chose this explicitly. Not mine to revisit without asking. |
| **REC→ACCEPTED** | I recommended it, Evan picked it from an options list. He owns the outcome; I own the framing. |
| **CLAUDE** | **I decided this on Evan's behalf.** ⚠️ These are the ones to review first. |
| **RESEARCH** | Forced by a verified external fact (usually legal). Not a preference. |

**Confidence** is my confidence the decision is right, not that it's implemented.
**Reversal cost** is what it costs to change course *after v1 ships*.

---

## A. Foundational decisions (interview rounds 1–4, verbatim record)

These four rounds are preserved verbatim in the session transcript, including
the exact alternatives offered.

### D-01 — Stack: Plotly Dash on Railway
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** high

Alternatives offered: FastAPI + React/Next; Streamlit; Next.js/TypeScript only.

Chosen because your `CLAUDE.md` toolchain (uv, pytest, ruff, ty, prek) is
Python-only, and `mccoy` already proved this exact deploy path. Plotly's
click-callbacks make the headline chart→table interaction native rather than
custom.

**Known cost, accepted:** Dash renders client-side, so SEO is poor and episode
text is invisible to non-rendering crawlers (PRD §4.1). The documented escape
hatch is a static-site migration in v2/v3.

**Revisit if:** you want this to rank in search, or you want per-episode pages
to preview correctly when shared as links.

### D-02 — Data model: offline pipeline → committed dataset
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** low

Alternatives offered: live API calls at runtime; hybrid static-core + live-extras.

No API keys in production, no rate limits on a recruiter's first visit, no flaky
tests, and instant page loads. The app never fetches at request time.

### D-03 — Corpus: seasons 1–11 + both films (220 records)
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** low

Alternatives offered: episodes only; seasons 1–9 only; include *The Lone
Gunmen* / *Millennium*.

Films are first-class rows but **excluded from the season chart** so bar heights
mean what they appear to mean (PRD §3.1). This is why films need nullable
`season`/`episode`/`production_code` — see **OPEN-01**, where that decision is
currently contradicted by the schema.

### D-04 — Three categories, not two
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** high

Alternatives offered: strict binary; binary + disputed flag; decide after seeing data.

Your original brief said "monster-of-the-week and the other kind." Research then
found four sources giving four different mythology counts (~60 / 70 / 71 / ~80),
disagreeing on **~22 episodes — 10% of the show**.

This grew into the design in PRD §5.2: store all three source labels, derive a
fourth, and **render the disagreement as a feature**. The PRD calls this "the
single most important design decision in the project," and I agree — it converts
an unwinnable argument into the most interesting thing on the site.

### D-05 — Classification authority: official Fox box sets + explicit rules
**Owner:** EVAN · **Confidence:** medium · **Reversal cost:** medium ·
**⚠️ Substantially revised by research**

Alternatives offered: Wikipedia/Fandom consensus; LLM classification; auto-sourced
then owner-reviewed.

You chose the Fox DVD box sets for their citable authority. Research then found
they cover only ~60 episodes, **predate the revival by a decade**, and omit
"Musings of a Cigarette Smoking Man." They could not serve as sole authority.

**What it became:** one of three weighted inputs, not the arbiter. Your
underlying intent — *a defensible, citable answer to "why is this MOTW?"* — is
preserved better by the three-source design than it would have been by the
original choice.

**Unresolved:** PRD §5.3's derivation rules are logically incomplete. See
**OPEN-01**.

### D-06 — AI-drafted prose, human-reviewed, with a review tool
**Owner:** EVAN · **Confidence:** high · **Reversal cost:** medium

You rejected all four options I offered and wrote your own:

> *"Use wikipedia and imdb (they have a section for trivia) generate and label as
> AI written, but allow me the ability to review and confirm. I need a tool to go
> through your writing and confirm and then label it human-reviewed."*

This was the single most consequential answer in the interview — it created the
review CLI, the two-state badge system, and the "edits are sacred" architecture.

**Two parts of it did not survive:**
- **IMDb trivia** — barred by C4 (no IMDb scraping/LLM ingestion). I flagged this
  risk when you answered and research confirmed it.
- **Synopses** — no lawful source exists for public republication (D-14).

**What survived:** the review workflow itself, now applied to ≤30-word original
loglines instead of trivia writeups. The mechanism is intact; the content it
governs is thinner than you asked for.

### D-07 — Edits are sacred; regeneration can never silently overwrite
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** high

Alternatives offered: approve/reject only; freeze reviewed episodes entirely.

Machine-owned and human-owned fields are separate layers. Any pipeline step
that would change human-reviewed content **emits a diff and changes nothing**.
Enforced by a test, and the guard *raises* rather than skipping — per your
`CLAUDE.md`: *do not hide or wrap errors*.

**Revisit if:** the scheduled refresh proves too noisy in practice. The
POSTMORTEM already flags this as an open question for the Execute phase.

### D-08 — Review tool is a local CLI
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** low

Alternatives offered: markdown + your editor; owner-only page in the Dash app;
CLI + public progress page.

A web reviewer would have forced auth, a session secret, and write-back storage
onto a public deployment — exactly the complexity `mccoy` had to absorb. A local
CLI needs none of it and is fully testable.

### D-09 — Data format: readable JSON source → built SQLite artifact
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** medium

Alternatives offered: SQLite as truth; JSON only, no build step; Parquet.

`git diff` on a binary SQLite file shows nothing — which would silently defeat
D-07. Readable diffs are the entire point of the review workflow. SQLite is a
regenerable build output, never committed as truth. FTS5 comes free for v2 search.

### D-10 — Testing: recorded fixtures + separate `@pytest.mark.network` suite
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** low

Alternatives offered: hand-written fixtures only; mock at client boundary;
fixtures + schema contract tests.

Parser tests run offline against recorded real payloads; a marked network suite
is excluded from CI and run manually to catch upstream drift.

### D-11 — Design: restrained modern, subtle X-Files signals
**Owner:** REC→ACCEPTED · **Confidence:** medium · **Reversal cost:** low

Alternatives offered: full X-Files aesthetic; clean analytics dashboard; match
existing portfolio.

Reads first as a serious data tool, with the fandom as charm rather than pitch.
Medium confidence only because this is taste, and taste is yours — it's also the
cheapest thing here to change later.

### D-12 — Playlists (and layered search) are v2
**Owner:** REC→ACCEPTED · **Confidence:** high · **Reversal cost:** low

You specified the search design in detail — **tags + full-text + semantic,
layered** — then scheduled it after v1. The design is captured in PRD §7 so v1's
data model doesn't foreclose it. Choosing SQLite (D-09) was partly to keep FTS5
available for exactly this.

### D-13 — v1 scope: the vertical slice, plus ratings
**Owner:** EVAN · **Confidence:** high · **Reversal cost:** low

You picked chart → click → table → links as the ASAP vertical slice, and from
the remaining feature list selected **only** "IMDb ratings + viewership charts"
for v1. Trivia writeups, people profiles, and interconnections were deferred but
fully specified so v1 wouldn't paint them into a corner.

Both halves of your one v1 addition then moved (D-14, D-16). **v1 is now thinner
than what you approved** — see **OPEN-04**.

---

## B. Decisions research overturned *after* you'd agreed

The intended payoff of front-loading feasibility into Requirements: four agreed
decisions were invalidated before any code existed. Detail in POSTMORTEM.md.

### D-14 — No IMDb ratings ❌ *(reverses your v1 pick)*
**Owner:** RESEARCH · **Confidence:** high · **Reversal cost:** n/a

IMDb's non-commercial license bars republication into any online database, and
OMDb holds no license to sublicense it. The licensed bulk product is **$50,000/yr**
(corrected from an initial $150,000 claim by adversarial verification).

**→ We ship TVmaze `rating.average` and *link* to IMDb pages.** Linking is
unrestricted. Now constraint **C1**.

**⚠️ Note the shape of this:** ratings were the one feature you added to v1, and
the substitute is a different, less recognized number. Flagged in **OPEN-04**.

### D-15 — No "Open in Hulu" button ❌ *(reverses your opening sentence)*
**Owner:** RESEARCH · **Confidence:** high · **Reversal cost:** n/a

Hulu's ToS bars scraping *and* unauthorized linking; there are no public
per-episode URLs; and Disney is folding Hulu into Disney+ in late 2026 — so even
hand-collected links would rot.

**→ We link to the TMDB season watch page:** sanctioned, provider-agnostic, and
it auto-updates when the show moves. Now constraint **C7**.

**Honest accounting:** you said "I have a hulu account" and asked for this
first. You do not get a one-click-to-the-episode button. You get one click to a
page that tells you where it's streaming.

### D-16 — Railway always-on, ~$5/mo
**Owner:** RESEARCH → needs your sign-off · **Confidence:** high

Railway sleeps after ~10 min idle and the first request to a slept service can
return **502** — landing on precisely the recruiter this site exists to impress.

**⚠️ This spends your money and I never asked.** See **OPEN-02**.

### D-17 — Original ≤30-word loglines, not synopses
**Owner:** RESEARCH · **Confidence:** high · **Reversal cost:** low

No lawful source of episode synopses exists for public republication — **0 of
220**. Every source is either CC BY-SA (ShareAlike attaches to your whole
dataset) or non-commercial. *Twin Peaks Productions v. Publications
International* held detailed plot recounting non-transformative.

A ≤30-word original logline sits far short of that line. Now constraint **C3**.

### D-18 — No show imagery at all
**Owner:** CLAUDE ⚠️ · **Confidence:** medium · **Reversal cost:** low

No source offers a clean per-image license for public use, and the wordmark and
X-glyph are live trademarks (USPTO Reg. 5555723).

**This is a risk-posture call I made for you, and it is not settled law** —
§107 fair use has protected screenshots in comparable contexts. I chose the
conservative posture because the downside is asymmetric: a takedown on a
portfolio piece is worse than a plainer-looking site.

It also forces a more interesting visual design, since the site can't lean on
stills. Now constraint **C2**. See **OPEN-03**.

---

## C. Decisions I made on your behalf ⚠️ *review these first*

Beyond D-18, these were not put to you as questions. Most were made after the
session hit its usage limit, under your instruction to go with my
recommendations.

| # | Decision | Why | Reversal cost |
|---|---|---|---|
| D-19 | **Project renamed `x-files_data` → `spooky`** | Portfolio siblings are all single evocative words (enki, lucre, mccoy, guzzolene, elvis, bartleby). `x-files_data` also names a trademark directly in a public repo URL. | **Low now, high after the repo is public and linked.** |
| D-20 | **Added a "Project-specific rules" section to CLAUDE.md** | The Execute phase has real legal landmines and CLAUDE.md is the only file guaranteed to be read. It is explicitly marked as an addition you may delete. | Trivial |
| D-21 | **Ternary category names: Mythology / Monster-of-the-Week / Standalone** | "Standalone" beat "Other" — it's what fans actually say, and it describes rather than dismisses. | Trivial |
| D-22 | **Trivia writeups demoted from v1 to v2** | Your chosen v1 was already tight, and C4 removed IMDb trivia — the richest source. Wikipedia-only trivia is much thinner than what you pictured. | Low |
| D-23 | **Viewership demoted to v2** | **All four viewership claims failed verification** when research agents died. Gated on hand-QA of the Wikipedia column rather than shipped on unverified data. | Low |
| D-24 | **Video extras dropped entirely** | Every claim in this area failed verification. Official BTS content is ~5 items, all from the 2016 revival; the rest is fan rips with active link-rot. | Low |
| D-25 | **Contemporary review sentiment recorded as *unassessed*, not rejected** | That research agent errored and produced nothing. Recording it as "rejected" would have destroyed the information that we never actually looked. | Trivial |
| D-26 | **Publish the derived dataset as CC BY-SA** | C6 — ShareAlike attaches from Wikipedia/TVmaze inputs. Also a genuine portfolio artifact in its own right. | Medium |
| D-27 | **~110 tasks, each with a `Verify:` line** | The RECL Execute prompt is *"Stop if you have questions"* — so TASKS.md had to meet a self-sufficiency bar. Verify lines exist so the Check phase has evidence rather than "should work." | Low |

---

## D. Open items needing your decision

### OPEN-01 — The classification derivation rules are logically incomplete 🔴
**Blocks:** the Execute phase, at Group E.

PRD §5.3's five rules assume three non-null source labels, but:
- §5.2 permits `label_fox_dvd: null`, and rule 2 ("≥2 of 3") is undefined when a
  vote is missing.
- The **two films have no Wikipedia dagger and no dom111 label**, yet §5.2 types
  those fields as non-nullable — so films cannot be classified at all as written.
- §5.3's rules classify *Fight the Future* as **monster-of-the-week**, while
  §8.1 and task E-04 both assert it is **mythology**. A direct contradiction.
- Rule 4 depends on a hand-maintained `has_creature` flag, but no task ever
  confirms it and the review CLI is specified for loglines only.

**My recommendation:** treat a null source as *abstaining* — compute the majority
over non-null votes only, and mark any record with fewer than three votes
`contested = true` automatically. Films then classify on dom111 alone (or a
hand override), which is honest and visible in the UI. This needs your ruling
because it changes what the headline chart shows.

### OPEN-02 — The $5/month is not yet authorized 🟡
D-16 commits you to ~$5/mo for always-on Railway. I decided that for you on
engineering grounds. **Confirm, or accept cold-start 502s and keep it free.**

### OPEN-03 — The no-imagery posture is conservative, not required 🟡
D-18 is my risk judgment, not settled law. A site with zero show imagery looks
noticeably plainer. If you'd rather run modest fair-use risk — a small number of
low-resolution stills with attribution — that is a legitimate call, and it's
**yours**, not mine. Say so and I'll revise C2 and the design accordingly.

### OPEN-04 — v1 is now thinner than what you approved 🟡
You approved v1 = vertical slice + **IMDb ratings + viewership charts**. Since
then: IMDb ratings → TVmaze ratings (D-14), viewership → v2 (D-23). So the one
feature you added to v1 is substantially gone.

**Options:** (a) ship the thin v1 fast and iterate — my recommendation, it's
still a complete, correct, deployed product; (b) pull viewership back into v1
and pay for the hand-QA; (c) pull a v2 feature forward to give v1 more substance.

### OPEN-05 — What to do with the 175 unverified review findings 🟡
An adversarial review produced 175 findings (37 blockers). **None were ever
verified** — that pass died on the session limit. Of the five I checked by hand,
**two were plain wrong** (§E.1).

**My recommendation:** retire them as a batch. See §E.6 for the reasoning. Adopt
the handful already confirmed, keep §E.3 (the `build/NN_*.py` naming problem) as
a live item, and let the rest go.

**Your call**, because the alternative — a fresh full triage — is a real token
spend that I'd rather put into Group D.

---

## E. Triage results

### E.1 — Adjudicated by hand, with evidence *(2026-07-27)*

Each of these was checked by **running the command or reading the file**, not by
trusting the finding. Note that two of five allegations were **wrong** — which is
the argument for verifying before acting.

| Finding | Verdict | Evidence | Action |
|---|---|---|---|
| Verify lines use unquoted `--include=*.py`, which breaks in zsh | ✅ **REAL** | `zsh -c 'grep -r x --include=*.py .'` → `zsh:1: no matches found: --include=*.py` | **Fixed.** Quoted the glob in C-10, H-01, J-01. |
| H-01's imagery check can never pass | ✅ **REAL — and worse than alleged** | The check returned **78**, all from `.venv/lib/python3.14/site-packages/`. It scanned the virtualenv. | **Fixed.** Added `--exclude-dir='.venv' --exclude-dir='.git'`. Now returns 0, and *discriminates*: planting one `.png` reference makes it return 1. |
| A-13 references a CI template that doesn't exist | ❌ **WRONG** | `../templates/python/.github/workflows/ci.yml` exists (509 bytes, Jul 2). A-13 is already `[x]`. | None. Do not act. |
| `curl … \| grep` can't work because Dash renders client-side | ❌ **WRONG** | Ran the app and curled it. `grep -c "unofficial fan project"` → **1**; `grep -c "spooky"` → **1**. The attribution sits in a server-rendered `<noscript>` block, `app.py:30-42`. | None. C-14/C-18/H-08/J-06 are fine as written. |
| Dash client-side rendering hurts SEO | ✅ **REAL, already known** | Same run: `grep -c "Squeeze"` → **0**. No episode text in served HTML. | None — PRD §4.1 already accepts this and documents the static-site escape hatch. |

### E.2 — Fixed: no `tests/conftest.py` *(CLAUDE.md violation)*

`CLAUDE.md` requires *"use pytest fixtures in conftest.py to DRY,"* but five test
files existed with no conftest. `load_episodes(Path("data/episodes_sample"))` was
duplicated at **7 call sites**, and because the path was **relative**, the suite
only passed when pytest ran from the repo root.

**Fixed.** Added `tests/conftest.py` with `sample_data_dir`, `episodes_df`,
`contested_record`, and `render_text`, anchored to the repo root via
`Path(__file__).resolve().parent.parent`.

- `uv run pytest` → **11 passed**; ruff and ty clean.
- Runtime **1.49s → 0.57s** (session-scoped loading).
- Now passes from any cwd — verified by running from `tests/`: **11 passed**.
- `episodes_df` hands out a deep copy per test, so `test_chart`'s film-injection
  cannot leak into another test.

### E.3 — Still open, latent, will bite at Group D 🔴

**`build/NN_*.py` module names are not importable.** TASKS.md specifies
`build/01_spine.py` … `build/09_emit.py`. A Python identifier cannot begin with a
digit, so `import build.01_spine` is a syntax error and no test can import them —
which makes every *"→ green"* Verify in Groups D–F impossible as written.

Not yet a problem only because `build/` is still empty. **My recommendation:**
rename to `build/spine.py`, `build/wikipedia.py`, `build/merge.py`, `build/emit.py`,
and keep run order in an explicit driver (`build/__main__.py`) rather than encoding
it in filenames. Ordering belongs in code, not in a naming convention that fights
the language.

*Not yet applied — this rewrites task IDs across four groups, so it wants your nod.*

### E.4 — Three real bugs found by driving the running app 🐞

None of these were in the 175 findings. All were found by opening the app in a
browser and clicking, and all are now fixed with tests.

**1. Chart clicks silently dropped the season** *(C-15 — the headline feature)*

Clicking season 5's Mythology segment filtered to *"All seasons · Mythology"* —
4 rows across seasons 1, 5, and 10 instead of 1 row. Category registered; season
was discarded.

Cause: `dcc.Location(id="url")` at app.py:164 left `refresh` at Dash's default of
`True`, so writing `pathname` and `search` from one callback triggered a real
browser navigation that threw the pathname away. The callback logic was correct
all along — proven by three tests that pass against it unchanged.

**Fixed:** `refresh=False`. Verified in-browser: season 1 → 2 rows, season 5 →
1 row, season 10 → 1 row, each matching Plotly's own tooltip.

**2. `nan` rendered on the site's most important feature** 🔴

The contested-episode breakdown displayed:

> `Fox DVDs: nan · Wikipedia: mythology · dom111: mythology`

Cause: JSON `null` becomes `float('nan')` through pandas, so `value is None` is
**False** and the f-string interpolated the literal string `"nan"`. Every season
10–11 record has a null `label_fox_dvd` (the Fox DVDs predate the revival), so
this was the *common* case on the contested view — the thing PRD §5.2 calls the
most interesting thing on the site.

**Fixed:** renders `no data` — and deliberately distinguishes that from
`not listed`. A source that never covered a record is not the same as a source
that covered it and declined to flag it. Collapsing them would misrepresent the
evidence.

**3. Any film would have crashed the app** 🔴

`spooky/links.py::tmdb_watch_url` guarded with `season is not None`, then called
`int(season)`. Films have no season, and pandas supplies `pd.NA` — which is not
`None` — so `int(pd.NA)` raises `TypeError`. Films are first-class records
(PRD §3.1, decision D-03) and there are 2 in the real 220-record corpus.

Latent only because the 12 sample records contain no film. It would have fired
the first time real data loaded.

**Fixed:** added `spooky/values.py` with `is_missing()` and `as_int()` covering
all three null shapes (`None`, `float('nan')`, `pd.NA`), and routed panel and
link code through it.

> **The general lesson, worth carrying into Group D:** a JSON `null` does not
> reach the app as `None`. Every `is None` check against record data is
> suspect. The ingest pipeline will produce far more nulls than the sample
> data does.

### E.5 — Group C verified and checked off

Group C's checkboxes were all unchecked even though the code was written. Each
task's Verify line was actually run; **C-01 … C-18 now checked off** (31 of 122
tasks). C-19 (Railway deploy) and C-20 (the gate) remain open — C-19 needs the
account and the always-on setting from **OPEN-02**.

Evidence: `uv run pytest` → **29 passed**; `ruff check` clean; `ty check` clean;
chart-click, row-click, and URL routing each confirmed in a live browser.

### E.6 — Full triage run *(abandoned, deliberately)*

The workflow clustering all 175 findings **stalled** — one agent, 13 minutes with
no output, no result emitted. Stopped rather than left running. The previous
session died the same way (81 of 93 agents lost to a usage limit), so I did not
relaunch at that scale.

**Recommendation:** don't re-run the 175 findings as a batch. They are 3 hours
stale, ~40% appear already-fixed or wrong (2 of the 5 I checked by hand were
plain wrong), and the genuinely valuable bugs in this session came from *running
the app*, not from re-reading the documents. Better use of the same tokens: work
Group D with the app open, and adjudicate individual findings on contact.

---

## F. Decision provenance — an honest note

The POSTMORTEM records **9 interview rounds and 36 decisions**. Only rounds 1–4
(16 decisions, D-01 through D-13) survive verbatim in the current session
context, with their exact alternatives.

Decisions from rounds 5–9 are recorded in `PRD.md` as outcomes, but **the
options considered and the wording of those questions are not recoverable from
my context** — they were summarized away when the session compacted. I have
reconstructed them here only where `PRD.md` states them directly, and I have
not invented alternatives I cannot source.

If a decision in PRD.md isn't in this register, that's why. It was still made
deliberately — just not in a form I can now reproduce faithfully.
