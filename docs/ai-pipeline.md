# The logline pipeline — design notes

Every episode needs a one-sentence teaser. Writing 220 by hand is slow; copying
them from a source is illegal (CLAUDE.md bars verbatim synopses, and caps
loglines at 30 words). So loglines are **AI-drafted from factual inputs, guarded
mechanically, graded, corrected, and then handed to a human to approve** — a
four-stage loop where the model does the drafting and the guardrails, not hope,
enforce the rules.

This document is the "why" behind that loop. Every claim points at the code.

```
  ┌── generate ──┐   ┌── triage ──┐   ┌── rewrite ──┐   ┌── review ──┐
  │ draft_logline│──▶│ grade A/B/C│──▶│ fix the C/B │──▶│ human sign │
  │ (Anthropic)  │   │ + critique │   │ from critique│   │ -off (CLI) │
  └──────────────┘   └────────────┘   └─────────────┘   └────────────┘
   build/loglines.py  tools/triage.py  build/rewrite.py  tools/review.py
        │                                                      │
        └── writes logline_generated ──────────┐   copies ─────┘
            review_status: "ai-drafted"        ▼   → logline, "human-reviewed"
                              machine layer  ┆  human layer (sacred)
```

## 1. Generate — grounded, capped, original

`build/loglines.py::draft_logline` drafts one logline per record from **factual
inputs only** — title, air date, credits, classification, and the episode's
Wikipedia Production/Themes sections (`_facts`). The system prompt tells the
model to ground itself in those facts and its own knowledge, and to *stay general
rather than guess* when unsure.

Two rules are then enforced **mechanically**, not by asking the model nicely:

- **≤30 words.** `len(draft.split()) > WORD_CAP` → reject and re-request.
- **No verbatim run of >8 words from any source.**
  `build/loglines.py::contains_verbatim_run` is a real word-shingling check
  (case-insensitive, `MAX_VERBATIM_RUN = 8`), not a prompt instruction. If a
  draft trips it, the loop retries with corrective feedback.

The step writes `logline_generated` and sets `review_status: "ai-drafted"`. It
**never** writes `logline`, and it skips any `human-reviewed` record before
making an API call. That separation is the whole ballgame — see §5.

## 2. Triage — a cheap read-only grader

Reading 220 drafts cold is the slow part of review. `tools/triage.py::grade_all`
runs a second, cheaper pass that grades each draft **A / B / C** with a one-line
critique (`grade_record` → `parse_verdict`), written to
`data/logline_triage.json`. It never opens an episode file for writing — grading
is advice, not a review — and it flushes the grade file after **every** record so
a crash can't discard grades already earned (an early run lost 214 that way).

The grades let the review CLI order its queue worst-first and show the critique
inline, so the human spends attention where it's needed.

## 3. Rewrite — a self-correction loop that measurably works

The triage critiques are structured feedback ("invents a kidnapping", "it's a
missile silo, not a UN bunker"), not vibes. `build/rewrite.py::rewrite_logline`
feeds each draft **plus its critique as an editor's note** back to the model and
asks for a corrected draft, under the same ≤30-word / no-verbatim guardrails. It
stays `ai-drafted` — a better machine draft, still awaiting human sign-off.

**The result is measurable** — the reason this loop exists rather than a single
draft pass. Triage grades over the 218 TV drafts, before and after the corrective
rewrite pass:

| Grade | Before | After |
|-------|-------:|------:|
| **A** — ship as-is | 117 | **171** |
| **B** — minor nit | 87 | 45 |
| **C** — rewrite (likely wrong) | 14 | **2** |

The C's are the important column: they were factual hallucinations the triage
pass had already diagnosed (identical fathers who weren't identical, an invented
kidnapping, a missile silo mislabeled a UN bunker). Feeding the diagnosis back
fixed 13 of 15; the 2 survivors carry factual notes and sort first in the human
queue. **A-grade drafts rose from 54% to 78% of the corpus** — that many fewer
drafts a human has to rewrite by hand.

## 4. Refusal handling — fail fast, don't abort the batch

One episode is titled `Rm9sbG93ZXJz` (base64 for "Followers"). That opaque string
deterministically trips the safety classifier, so the model returns
`stop_reason: "refusal"` for it every time. Both `grade_record` and
`rewrite_logline` check for this **before** reading content and **fail fast** —
retrying a deterministic refusal only burns calls, and a refusal must never be
mistaken for a token-budget truncation. The batch functions
(`triage.py::grade_all`, `rewrite.py::rewrite_all`) catch that failure, log it
loudly, keep going, and surface it with a non-zero exit — so one refusal costs
one record (which keeps its prior draft for hand review), not the whole run.

## 5. Provenance — the machine layer and the sacred human layer

Fields are split into two layers:

- **Machine-owned:** `logline_generated`, and the `review_status` state machine
  (`ai-drafted` → `needs-work` → `human-reviewed`).
- **Human-owned (sacred):** `logline`, `reviewed_at`, `review_note`.

Only `tools/review.py` promotes across the boundary: **approve** copies
`logline_generated` → `logline` and stamps `human-reviewed`; **edit** stores the
human's own wording; **reject** files a note and leaves the draft pending.
Approving is an explicit keystroke — a bare Enter never approves.

The boundary is enforced, not trusted. `build/merge.py::guard_human_fields`
refuses to overwrite any human-owned field on a `human-reviewed` record — it
raises with a diff rather than clobbering, so no pipeline step (including the
monthly scheduled refresh) can silently overwrite human judgment. Regenerating
loglines over reviewed records makes **zero** API calls and changes nothing.

## 6. Instrumentation — what a run costs

The three API-calling steps accumulate token usage, latency, retries, and
refusals (`build/_usage.py::UsageAccumulator`) and log one line at the end of a
batch. A representative triage sample:

```
RUN SUMMARY: 20 records · 7331 input + 372 output tokens · ~$0.03 est
(claude-sonnet-4-6) · median 1.5s / max 2.4s latency · 0 retries · 0 refusals
```

At ~370 input / ~19 output tokens per record, a full 218-draft triage pass is
roughly **$0.30**. The model is pinned to `claude-sonnet-4-6` — cost-appropriate
for a batch classification/generation job over a few hundred records.

## Honest status

Drafts are **AI-drafted, guarded, and measured** — not human-reviewed. As of this
writing 1 of 220 records is `human-reviewed`; the rest await the owner's pass
through `tools/review.py` (worst-first, critiques inline). The pipeline's job is
to make that pass fast and safe, not to skip it. The published dataset displays
`logline_generated` behind an **AI-drafted** badge until a human approves it.
