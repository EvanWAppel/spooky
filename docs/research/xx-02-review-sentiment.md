# XX-02 — Contemporary review sentiment: sources, licences, recommendation

**Status:** researched 2026-10-22, **awaiting Evan's decision**. Research only:
nothing here is built, no dependency was added, and no key was used.
This is not legal advice. It applies the project's own rules (CLAUDE.md, PRD §2
C1–C7 and §11) to the candidate sources.

**Why this exists.** The original feasibility agent for this topic errored and
produced nothing (DECISIONS D-25, PRD §12), so the feature was recorded as
*unassessed*. This memo redoes that research.

**Not consulted, by rule (C4):** Fandom, TV Tropes, IMDb, Pluto TV,
insidethex.co.uk. None of them was fetched for this memo.

---

## 1. What "review sentiment" could mean here

Three distinct features hide under the name. They carry different legal risk:

| Shape | Example on an episode page | Risk driver |
|---|---|---|
| **A. Quotes** | *"profoundly creepy" — Entertainment Weekly* | Reproduces third-party copyrighted text |
| **B. Cited grades (facts)** | *A.V. Club A−, EW B+ (via Wikipedia)* | Contract terms of the grade's origin; *Feist* selection |
| **C. Computed score** | *Critics: mostly positive* | How the input was obtained, and whether an LLM read it |

## 2. Candidate sources

| # | Source | Licence / terms | Episode coverage | Verdict |
|---|---|---|---|---|
| 1 | **Wikipedia per-episode "Reception" sections** | Prose CC BY-SA 4.0 (already used, already footered). **But** the critic quotes embedded in that prose are *not* CC BY-SA: Wikipedia carries them as fair-use non-free content.[^nfc] | Measured below: 212 of 213 fetched episode articles have a Reception section | **Best substrate**, with care over quotes |
| 2 | **The original reviews** (A.V. Club series rewatch, Entertainment Weekly's 1990s grades, Den of Geek, Television Without Pity recaps, period newspapers) | All rights reserved, under each publisher's own terms of use; many paywalled or defunct | Wide (the A.V. Club covers almost every episode) | **Link only.** Reading by hand to check a fact is fine; scraping, bulk copying or LLM-feeding is not |
| 3 | **Rotten Tomatoes** | ToU bars robots/scrapers/"automated means", bars publishing or distributing material except for personal non-commercial use, and bars using content to train or improve any AI tool[^rt] | Sparse per-episode, mostly the 2016/2018 revival | **Excluded**: contract-barred, same posture as IMDb (C1) |
| 4 | **Metacritic** | Terms page did not resolve (HTTP 404 at `metacritic.com/terms-of-use/` on 2026-10-22), so **unverified**. Metacritic scores seasons, not episodes, and only the revival seasons | Season-level only | **Excluded**: wrong granularity, terms unverified |
| 5 | **TMDB user ratings** | API terms bar caching longer than 6 months, use "in connection with a 'destination' website", and any use of TMDB content with an ML/AI application[^tmdb] | Per-episode `vote_average` exists | **Excluded**: audience, not critics, and the terms fight an SSR data site |
| 6 | **TVmaze ratings** | CC BY-SA 4.0[^tvmaze] | Already shipped | Already present. Audience score, not critic sentiment, so it doesn't answer XX-02 |
| 7 | **Wikidata `review score` (P444)** | CC0. String value with qualifiers `review score by` (P447), `point in time` (P585) and others[^p444] | **0** statements across the 234 items whose `part of the series` is *The X-Files* (Q2744), SPARQL run 2026-10-22 | **Empty today.** A clean CC0 home if anyone ever populates it |
| 8 | **Trakt** | API docs did not render to a fetcher; terms **unverified** | Per-episode user ratings | Not pursued: audience score, unverified terms |

### Coverage measurement (source 1)

A one-off script in the session scratchpad (not committed, not a pipeline step)
pulled current wikitext for every record's `enwiki_title` through the MediaWiki
API on 2026-10-22. It printed aggregate counts only:

```
records with enwiki_title: 214 (of 220 records)
articles fetched: 213
with a Reception section: 212
reception sections mentioning a letter grade (heuristic): 105
reception prose words: median 387 min 59 max 1103
top cited outlets in Reception sections (articles citing):
   180  The A.V. Club
   118  20th Century Studios
    90  Entertainment Weekly
    89  The Onion
    59  Fox Broadcasting Corporation
    44  Television Without Pity
    43  Den of Geek
```

How to read it:

- Coverage is near-total. Wikipedia is a realistic single substrate.
- "Contemporary" is mostly **not** contemporary. The most-cited critic is the
  A.V. Club (The Onion is its historical publisher), whose X-Files reviews are a
  2008-onward retrospective rewatch. Broadcast-era voices are mainly
  Entertainment Weekly's 1990s grades. Any feature must carry the **review date**,
  or it will present 2010 hindsight as 1995 reception.
- Fox/20th Century citations are mostly Nielsen and DVD sources, not critics.
- The grade count is a regex heuristic. Treat it as "about half", not a number to
  ship. Re-derive at build time, per CLAUDE.md.

## 3. Is quoting or scoring lawful under CLAUDE.md?

**A. Quotes: not recommended.** CLAUDE.md doesn't name critic quotes, but:
- Wikipedia's CC BY-SA licence doesn't cover them. Wikipedia includes them as
  brief fair-use excerpts.[^nfc] Copying them out of Wikipedia means relying on
  *our own* fair-use defence, not on the licence.
- Systematically lifting the most quotable line from each of ~200 reviews into
  a database is a weaker fair-use position than one article quoting one critic
  in commentary. The project's posture is risk management (PRD §11.3), and this
  adds risk for little gain.
- Quotes tend to describe plot, which is C3 territory.

**B. Cited grades as facts: lawful, with caveats.** A grade such as "B+" is a
short fact about a review, the same class as the TVmaze ratings we already ship
(PRD §11.1). Caveats:
- Only take grades from the CC BY-SA Wikipedia prose, where an editor has already
  stated them with a citation. Never collect them from the outlet's site:
  publisher terms govern that, and source 3 shows how an aggregator's terms bite.
- *Feist* (PRD §11.3): a complete column of one outlet's grades mirrors that
  outlet's selection. Showing grades as "reported on Wikipedia, cited to X" per
  episode, with a link to the review, is the conservative form.
- Grades must be human-verified before showing. Wikipedia prose phrases grades
  inconsistently, and spot-checking one review page while researching this memo
  turned up an attribution that didn't match the Wikipedia text.

**C. Computed score: lawful only for some inputs.**
- Over the **original reviews**: no. That means bulk-copying copyrighted text,
  and for an LLM it is the ingestion that C4's reasoning exists to prevent. On RT
  or TMDB it is contract-barred outright.[^rt][^tmdb]
- Over **Wikipedia Reception prose**: allowed by CLAUDE.md. Wikipedia is
  permitted LLM input, and the logline pipeline already feeds it Production and
  Themes sections. The output is an original computed metric (PRD §11.1 "safe").
  Two catches: the embedded quotes are still third-party text (fine to *read*,
  never to *emit*), and an LLM pass needs `ANTHROPIC_API_KEY`, a paid key. That
  is Evan's call and sits behind the key-isolation item already in `BLOCKED.md`.
- A lexicon scorer (e.g. VADER) would avoid the key but adds a dependency and
  reads critical prose badly ("profoundly creepy" is praise). Not recommended.

## 4. Recommendation

1. **Don't build "sentiment" as a free-text score.** Build, if anything,
   **cited critic grades**: per episode, the `(outlet, grade, review year,
   citation URL)` tuples that the Wikipedia Reception section already states.
   Extract them deterministically from the wikitext the pipeline already
   exports (`build/articles.py`), record `source = Wikipedia`, `license = CC BY-SA
   4.0` per field (CLAUDE.md data rules), and put every tuple through the existing
   review CLI as `ai-drafted → human-reviewed`. It needs no new source, no new
   licence, no paid key and no new dependency.
2. **It fits the site's thesis.** The headline feature is that *sources
   disagree* on mythology labels. Critics disagree too: "EW B+, A.V. Club A−,
   1994 vs 2008" is the same story of open disagreement, told with facts.
3. **Show the date prominently and label it honestly.** "Critical reception
   (from Wikipedia)", not "contemporary reviews", unless a filter keeps only
   broadcast-era reviews.
4. **No quotes. No RT, Metacritic, TMDB or Trakt numbers. No LLM over original
   reviews.**
5. An LLM-drafted one-word consensus (positive / mixed / negative) over the
   Wikipedia prose is a possible **phase 2**, gated on the scoped, capped key and
   routed through human review like loglines.

## 5. Open questions for Evan

1. **Do you want this feature at all**, or should XX-02 close as "researched,
   declined"?
2. **Risk appetite on grades.** Are critic letter grades, cited through
   Wikipedia, acceptable as "facts" under PRD §11.1? (This memo thinks yes, but it
   is a judgement call, and the posture so far has been conservative.)
3. **Scope of "contemporary".** Broadcast-era only (1993–2002 and the revival's
   own air dates), or all critical reception including retrospectives? This
   decides whether the A.V. Club, the best-covered outlet, is in or out.
4. **Phase 2 LLM consensus.** Worth a paid key once it is scoped and capped, or
   facts only?
5. **Placement.** SSR episode pages only, or also a sortable column in the Dash
   explorer? (A column invites ranking episodes by a single outlet's grades, which
   sharpens the *Feist* selection concern.)

---

[^nfc]: Wikipedia, *Non-free content* policy: brief attributed verbatim quotations of copyrighted text are allowed, and "extensive quotation of copyrighted text is prohibited". These are used under fair use, not CC BY-SA. <https://en.wikipedia.org/wiki/Wikipedia:Non-free_content>
[^rt]: Rotten Tomatoes, *Terms of Use* (bans on automated collection, publication and AI training). <https://www.rottentomatoes.com/policies/terms-of-use>
[^tmdb]: TMDB, *API Terms of Use* (6-month cache limit, the "destination website" clause, the ML/AI prohibition). <https://www.themoviedb.org/api-terms-of-use>
[^tvmaze]: TVmaze API, "Use of the TVmaze API is licensed by CC BY-SA." <https://www.tvmaze.com/api>
[^p444]: Wikidata, *Property:P444 (review score)*. <https://www.wikidata.org/wiki/Property:P444>. Query endpoint used for the count: <https://query.wikidata.org/sparql>.

Other URLs referenced: Wikipedia episode article used to check Reception-section
structure, <https://en.wikipedia.org/wiki/Squeeze_(The_X-Files)>. Metacritic terms
(404 on 2026-10-22), <https://www.metacritic.com/terms-of-use/>. Trakt API docs (did
not render), <https://trakt.docs.apiary.io/>.
