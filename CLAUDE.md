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
