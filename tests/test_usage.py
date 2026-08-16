"""Tests for the pipeline usage/cost/latency accountant (build/_usage.py).

The accumulator is additive instrumentation: it records token usage, latency,
retries, and refusals across a pipeline run and prints one summary line. It
never touches an episode record and must degrade gracefully when a response
carries no ``usage`` (the test stubs don't).
"""

from __future__ import annotations

from types import SimpleNamespace

from build._usage import UsageAccumulator


def _response(input_tokens: int, output_tokens: int):
    return SimpleNamespace(
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    )


def test_accumulates_tokens_and_records() -> None:
    acc = UsageAccumulator(model="claude-sonnet-4-6")
    acc.record(_response(100, 20), latency=1.0, attempts=1)
    acc.record(_response(150, 30), latency=2.0, attempts=1)

    assert acc.records == 2
    assert acc.input_tokens == 250
    assert acc.output_tokens == 50


def test_counts_retries_from_attempts() -> None:
    acc = UsageAccumulator(model="claude-sonnet-4-6")
    acc.record(_response(10, 5), latency=1.0, attempts=1)  # no retry
    acc.record(_response(10, 5), latency=1.0, attempts=3)  # 2 retries

    assert acc.retries == 2


def test_notes_refusals_without_a_record() -> None:
    acc = UsageAccumulator(model="claude-sonnet-4-6")
    acc.note_refusal()
    acc.note_refusal()

    assert acc.refusals == 2
    assert acc.records == 0


def test_handles_a_response_with_no_usage() -> None:
    """The test StubClients return content-only responses — never crash."""
    acc = UsageAccumulator(model="claude-sonnet-4-6")
    acc.record(SimpleNamespace(content=[]), latency=0.5, attempts=1)

    assert acc.records == 1
    assert acc.input_tokens == 0
    assert acc.output_tokens == 0


def test_median_and_max_latency() -> None:
    acc = UsageAccumulator(model="claude-sonnet-4-6")
    for latency in (3.0, 1.0, 2.0):
        acc.record(_response(1, 1), latency=latency, attempts=1)

    assert acc.median_latency() == 2.0
    assert acc.max_latency() == 3.0


def test_cost_estimate_uses_the_model_price_table() -> None:
    acc = UsageAccumulator(model="claude-sonnet-4-6")  # $3 / $15 per Mtok
    acc.record(_response(1_000_000, 1_000_000), latency=1.0, attempts=1)

    assert acc.est_cost() == 18.0  # 1M * $3 + 1M * $15


def test_summary_reports_every_dimension() -> None:
    acc = UsageAccumulator(model="claude-sonnet-4-6")
    acc.record(_response(100, 20), latency=1.5, attempts=2)
    acc.note_refusal()

    line = acc.summary()
    assert line.startswith("RUN SUMMARY:")
    assert "1 records" in line
    assert "100 input" in line
    assert "20 output" in line
    assert "1 retries" in line
    assert "1 refusals" in line
    assert "claude-sonnet-4-6" in line
