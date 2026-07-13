"""Complexity-tiered teacher: route each call to the cheapest model that handles its output shape.

Single-scalar-field schemas (Q_ONE/A_ONE — one utterance or one grounded answer, the bulk of calls)
go to the FAST model; multi-field or nested schemas (coupled QA_ONE, PAIRS, GUIDED, CATALOG) — which
small local models garble (role confusion; reasoning models truncate mid-JSON) — go to the STRONG
model. Presents the Teacher interface so recipes/synth are unchanged; health counters aggregate both.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Iterable

from pydantic import BaseModel

from kbft.teacher import Teacher


class PoolTeacher:
    """Weighted pool of Teachers (same tier, different models/providers) with FALLBACK. Each call picks
    a primary by integer weight (weighted round-robin); if that model FAILS (empty result — error /
    rate-limit / bad JSON), the call falls through to the remaining members in order. So a fast primary
    (e.g. gemini-lite:1) carries normal load while a slower/cheaper backup (e.g. gpt-oss:0) only kicks
    in when the primary is unavailable — resilience without paying the backup's latency in the hot path.
    Weight 0 = fallback-only (never primary). Health counters aggregate all members."""

    def __init__(self, teachers: list[Teacher], weights: list[int] | None = None):
        if not teachers:
            raise ValueError("PoolTeacher needs at least one teacher")
        self.teachers = teachers
        w = weights if weights is not None else [1] * len(teachers)
        sched = [i for i, wi in enumerate(w) for _ in range(max(0, int(wi)))]
        self._sched = sched or [0]  # all-zero weights -> first model is primary
        self._i = 0
        self._lock = threading.Lock()

    def _primary(self) -> int:
        with self._lock:
            idx = self._sched[self._i % len(self._sched)]
            self._i += 1
        return idx

    def chat_json(self, *a, **k) -> Any:
        idx = self._primary()
        order = [idx] + [j for j in range(len(self.teachers)) if j != idx]  # then fall back to the rest
        for j in order:
            out = self.teachers[j].chat_json(*a, **k)
            if out:
                return out
        return {}

    def verify_grounded(self, *a, **k) -> bool:
        return self.teachers[self._primary()].verify_grounded(*a, **k)

    def parallel_map(self, fn: Callable, jobs: Iterable) -> list:
        return self.teachers[0].parallel_map(fn, jobs)

    @property
    def model(self) -> str:
        return "+".join(t.model.split("/")[-1] for t in self.teachers)

    @property
    def calls(self) -> int:
        return sum(t.calls for t in self.teachers)

    @property
    def failures(self) -> int:
        return sum(t.failures for t in self.teachers)

    @property
    def rejections(self) -> int:
        return sum(t.rejections for t in self.teachers)

    def failure_rate(self) -> float:
        c = self.calls
        return self.failures / c if c else 0.0


def call_tier(schema: type[BaseModel]) -> int:
    """Complexity tier a teacher call needs. 0 = one string field (a simple single-turn surface: a
    user utterance or one grounded answer) — a small local model can author it. 1 = anything coupled/
    multi-field/nested (QA_ONE/PAIRS/GUIDED/CATALOG/FORM_FILL: authoring both dialogue sides or several
    fields in one JSON), which small models garble. Extend with higher tiers as needed."""
    fields = schema.model_fields
    return 0 if len(fields) == 1 and next(iter(fields.values())).annotation is str else 1


class TieredTeacher:
    """Routes each teacher call to a tier by output-schema complexity (`call_tier`); each tier is a
    weighted-fallback PoolTeacher (or a bare Teacher). Lets a cheap local model serve tier 0 while a
    strong cloud model serves the coupled schemas. Composable: any set of integer tiers; a call with
    no exact tier falls up to the nearest higher configured tier (else the highest). Presents the
    Teacher interface so recipes are unchanged; health counters aggregate every tier."""

    def __init__(self, tiers: dict[int, Any]):
        if not tiers:
            raise ValueError("TieredTeacher needs at least one tier")
        self.tiers = tiers
        self._levels = sorted(tiers)  # ascending

    def _pool_for(self, tier: int):
        if tier in self.tiers:
            return self.tiers[tier]
        higher = [t for t in self._levels if t >= tier]
        return self.tiers[higher[0]] if higher else self.tiers[self._levels[-1]]

    def chat_json(self, system: str, user: str, response_model: type[BaseModel],
                  temperature: float = 0.8, max_tokens: int = 1536) -> Any:
        return self._pool_for(call_tier(response_model)).chat_json(
            system, user, response_model, temperature, max_tokens)

    def verify_grounded(self, question: str, results_block: str, answer: str) -> bool:
        # grounding judgement is a complex call — use the highest tier (strongest models)
        return self._pool_for(self._levels[-1]).verify_grounded(question, results_block, answer)

    def parallel_map(self, fn: Callable, jobs: Iterable) -> list:
        return self._pool_for(self._levels[0]).parallel_map(fn, jobs)

    # --- aggregate health (the driver gates on failure_rate and prints calls/failures) ---
    @property
    def calls(self) -> int:
        return sum(p.calls for p in self.tiers.values())

    @property
    def failures(self) -> int:
        return sum(p.failures for p in self.tiers.values())

    @property
    def rejections(self) -> int:
        return sum(p.rejections for p in self.tiers.values())

    def failure_rate(self) -> float:
        c = self.calls
        return self.failures / c if c else 0.0

    @property
    def model(self) -> str:
        return " | ".join(f"t{t}:{self.tiers[t].model}" for t in self._levels)
