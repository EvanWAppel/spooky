prime directive: don't do anything you're unclear about ask me about it.
use uv
run python tools with uv run python
do not edit pyproject.toml dependencies directly
use uv add LIB or uv add --dev LIB
use pytest to implement tdd
use pytest fixtures in conftest.py to DRY
use ruff to lint
use ty to typecheck
use prek for precommits
use logging to help ai debug
do not hide or wrap errors.

---

## Project-specific rules

> Added by Claude during the Requirements phase because the Execute phase has
> real legal landmines. Delete this section if you want CLAUDE.md to stay
> exactly as you dictated it — but read it first.

### Hard prohibitions — these are legal, not stylistic

- **Never republish IMDb ratings or vote counts**, from IMDb datasets, OMDb, or
  scraping. IMDb's non-commercial license bars republication into any online
  database. Linking to an IMDb page is fine; showing their number is not.
- **Never ship show imagery** — no screencaps, promo stills, episode artwork,
  or the stylized X-Files wordmark/X-glyph (USPTO Reg. 5555723). No hotlinking
  `static.tvmaze.com`. "The X-Files" as plain text only.
- **Never ship verbatim synopses or detailed plot recaps** from any source, in
  any wording. Loglines are capped at 30 words.
- **Never scrape or feed to an LLM**: Fandom, TV Tropes, IMDb, Pluto TV,
  insidethex.co.uk. Fandom's ToU bars AI ingestion specifically.
- **Never ship episode transcripts.**
- **Never write "no copyright infringement intended."** It has no legal effect.
- Wikipedia and TVmaze are CC BY-SA: attribution is required and the derived
  dataset must carry ShareAlike. The footer text in PRD.md §11 is verbatim.

### Data rules

- `data/episodes/*.json` is the source of truth and is hand-editable. The
  SQLite artifact is a build output — never edit it, never commit it as truth.
- **Human-reviewed content is sacred.** Any pipeline step, including the
  scheduled refresh, must refuse to overwrite a field whose
  `review_status == "human-reviewed"`. Machine-owned and human-owned fields are
  separate layers. If a refresh would change human-owned content, it emits a
  diff for review and changes nothing.
- Every ingested field records its source and license. No unattributed fields.
- Re-derive counts at build time. Do not hard-code "218" or "71" anywhere —
  upstream tables shift.

### Verification

- Every task in TASKS.md has a Verify line. Run it. The Check phase is the
  human's, so leave evidence: paste real command output, never "should work."
- Network tests are `@pytest.mark.network` and excluded from CI. Parser tests
  run against recorded fixtures in `tests/fixtures/` and must pass offline.

<!-- factotum:blocked-protocol -->
**Blockers → `BLOCKED.md` (system standard).** Anything only Evan can resolve — a credential, a deploy, external access, or a decision — goes in a root `BLOCKED.md`: one `- [ ]` per blocker, prefixed 🔴 blocking / 🟡 nice-to-have, **each with the specific steps a human takes to unblock it** (the action, where, any URL / path / env-var). Security-related blockers carry `[sec]` right after the emoji (`- [ ] 🔴 [sec] …`). _system's blocked-router scans every `BLOCKED.md` under `~/Documents` and mirrors open items into Evan's todo dashboard, so nothing waits on him invisibly. Keep the file even when nothing is blocked — heading plus "nothing blocked right now" and zero `- [ ]` lines. Full rule: Evan's global `~/.claude/CLAUDE.md`.
<!-- /factotum:blocked-protocol -->

<!-- factotum:recl-standing-rules -->
**ROCRLL** — this project follows Requirements → Orchestrate → Check → Review → Loop → Ledger.

- **Requirements.** Draft/keep a `PRD.md` via interview — walk every branch, don't guess.
  The interview also produces the `TASKS.md` grouping and seeds the Ledger.
- **Orchestrate.** Default is linear. Fan out to subagents **only when a task group has ≥3
  genuinely independent tasks**; give each its **own git worktree**, merge back one at a
  time, and remove each worktree and its branch once merged or abandoned.
  **Precondition:** the project must be its own standalone git repo. Worktrees are for
  overlapping-file work — disjoint-file fan-out may use lighter same-tree partitioning.
  **Agents are hands, you're the head:** subagents write code in their worktrees; they never
  inspect raw data or make design/verdict calls — those escalate to the orchestrator.
- **Check.** TDD, test-first. **The human inspects the data; the agent never sees raw data.**
  Run Check **centrally at the orchestrator** at each merge join, not inside each worktree:
  **affected tests + lint + typecheck at each join; the full suite once, before the group's
  final merge to main.**
- **Review.** Independent adversarial review on **every merge to the main line**. Default
  reviewer: a fresh-context same-model subagent; escalate cross-model for high-stakes/security.
  **High-severity findings block, but the human adjudicates them against the primary source** —
  reviewers over-call; never auto-action a finding. Everything below high is advisory.
- **Loop.** Iterate.
- **Ledger.** Record every **decision with a real trade-off** (chose X, rejected Y, why) in a
  `DECISIONS.md` append log. The agent drafts the entry; the human confirms it.

**Guardrails (always on):** TDD-first · nothing external sent/merged/published/deployed
without explicit human approval · the agent never sees raw data · **no autonomous
(Ralph-style) self-feeding loops** · **prime directive — if anything is unclear, stop and ask.**

**Standard artifacts:** `PRD.md` · `TASKS.md` (parallel groups marked) ·
`AGENTS.md`/`CLAUDE.md` · `DECISIONS.md` · `BLOCKED.md`.

<!-- /factotum:recl-standing-rules -->
