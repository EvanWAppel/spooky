"""Per-run usage, cost, and latency accounting for the logline pipeline.

Additive instrumentation only — the accumulator records what each Anthropic
call cost and how long it took, then logs one ``RUN SUMMARY`` line at the end
of a batch. It never reads or writes an episode record, and it degrades
gracefully when a response carries no ``usage`` block (the test stubs don't),
so wiring it in cannot change pipeline behaviour.

Prices are $ per million tokens (input, output) for the documented current
model ids; an unknown model estimates $0 rather than guessing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# $ / million tokens (input, output) — Anthropic list prices.
_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


@dataclass
class UsageAccumulator:
    """Running totals for one pipeline pass over the records."""

    model: str
    records: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    retries: int = 0
    refusals: int = 0
    latencies: list[float] = field(default_factory=list)

    def record(self, response: Any, *, latency: float, attempts: int) -> None:
        """Fold in one successful call. ``attempts`` includes the winning try,
        so ``attempts - 1`` retries preceded it."""
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.input_tokens += getattr(usage, "input_tokens", 0) or 0
            self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.records += 1
        self.retries += max(0, attempts - 1)
        self.latencies.append(latency)

    def note_refusal(self) -> None:
        """A deterministic refusal — counted, but no tokens/latency to record."""
        self.refusals += 1

    def est_cost(self) -> float:
        price_in, price_out = _PRICING.get(self.model, (0.0, 0.0))
        return self.input_tokens / 1e6 * price_in + self.output_tokens / 1e6 * price_out

    def median_latency(self) -> float:
        if not self.latencies:
            return 0.0
        ordered = sorted(self.latencies)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2

    def max_latency(self) -> float:
        return max(self.latencies) if self.latencies else 0.0

    def summary(self) -> str:
        latency = f"median {self.median_latency():.1f}s / max {self.max_latency():.1f}s"
        return (
            f"RUN SUMMARY: {self.records} records · "
            f"{self.input_tokens} input + {self.output_tokens} output tokens · "
            f"~${self.est_cost():.2f} est ({self.model}) · "
            f"{latency} latency · "
            f"{self.retries} retries · {self.refusals} refusals"
        )

    def log_summary(self) -> None:
        log.info("%s", self.summary())
