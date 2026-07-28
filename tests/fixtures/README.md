# Recorded test fixtures

Real API payloads, recorded once by `uv run python tools/record_fixtures.py`
and committed so parser tests run offline and deterministically. The separate
`pytest -m network` suite hits the live APIs to catch upstream drift.

These files are **test inputs, not the published dataset** — the legal-shape
rules in `CLAUDE.md` (no synopses, no imagery) apply to what the site and
`data/dist/` ship, and the emit step strips those fields. The raw upstream
content here is redistributed under its own licenses, attributed below.

| File | Source | Retrieved | License |
|---|---|---|---|
| `tvmaze_episodes.json` | [TVmaze API](https://api.tvmaze.com/shows/430/episodes) — *The X-Files* episodes, no specials | 2026-07-27 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `wiki_s03.txt` | Wikipedia, [The X-Files season 3](https://en.wikipedia.org/wiki/The_X-Files_season_3) (wikitext) | 2026-07-27 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `wiki_s10.txt` | Wikipedia, [The X-Files season 10](https://en.wikipedia.org/wiki/The_X-Files_season_10) (wikitext) | 2026-07-27 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `wiki_s11.txt` | Wikipedia, [The X-Files season 11](https://en.wikipedia.org/wiki/The_X-Files_season_11) (wikitext) | 2026-07-27 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |

Why these three seasons: S3 is the template-capitalization edge case
(`{{Double-dagger}}`), S10+S11 are the revival rows (6 + 10 episodes) whose
nested templates break regex-based parsers. See `tests/test_wikipedia.py`.

To re-record after an upstream change: run the tool, review the diff, and
update the hand-counted expectations in `tests/test_wikipedia.py` if row or
dagger counts moved.
