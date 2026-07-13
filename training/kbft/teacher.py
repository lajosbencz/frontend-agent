"""Teacher LLM client for compositional generation.

Generates only the natural-language surface (varied utterances, grounded answers) from facts the
caller supplies; structure (tool calls, ids, results) is produced deterministically by the recipes.
Any OpenAI-compatible endpoint works — local Ollama (`/v1`) or OpenRouter — via the `openai` SDK;
`instructor` enforces a pydantic response model per call (validated, typed). The SDK's built-in
`max_retries` handles rate-limit/5xx backoff; a disk cache spares re-billing identical calls.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import instructor
from diskcache import Cache
from openai import OpenAI
from pydantic import BaseModel

# OpenAI-compatible base URLs. Add a provider here to support another vendor.
_BASE = {
    "ollama": os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/") + "/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}
_CACHE_DIR = os.environ.get(
    "TEACHER_CACHE_DIR", str(Path(__file__).resolve().parents[1] / "data" / ".teacher_cache"))


# --- canonical teacher output shapes (validated by instructor) ---
class QAItem(BaseModel):
    q: str
    a: str


class QAItems(BaseModel):
    items: list[QAItem] = []


class UAItem(BaseModel):
    user: str
    answer: str


class UAItems(BaseModel):
    items: list[UAItem] = []


class GroundingVerdict(BaseModel):
    unsupported_claims: list[str] = []
    supported: bool = True


QA_SCHEMA = QAItems  # back-compat aliases: callers pass these as response models
UA_SCHEMA = UAItems


@dataclass
class Teacher:
    """Vendor-flexible teacher client. `provider` selects local Ollama or OpenRouter (or any
    OpenAI-compatible endpoint). The OpenRouter API key is read from ENV (never an arg or logged)."""

    provider: str = "ollama"                 # "ollama" | "openrouter"
    model: str = "qwen3.5:4b-q4_K_M"
    workers: int = 3
    seed: int = 20260707                     # sent to the sampler -> reproducible NL surface
    api_key_env: str = "OPENROUTER_API_KEY"  # ENV var holding the bearer key for remote providers
    cache: bool = True                       # memoize identical calls to disk (credit-sparing)

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self._client: Any = None
        self._cache = Cache(_CACHE_DIR) if self.cache and not os.environ.get("TEACHER_NO_CACHE") else None
        # aggregate health counters; a silently degraded teacher hollows out whole recipe classes.
        self.calls = 0
        self.failures = 0
        self.rejections = 0  # grounding-verifier rejections (faithfulness gate) — surfaced by the driver

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = self._build_client()
        return self._client

    def _build_client(self):
        base = _BASE.get(self.provider, _BASE["ollama"])
        if self.provider == "ollama":
            key = "ollama"
        else:
            key = os.environ.get(self.api_key_env)
            if not key:
                raise RuntimeError(f"{self.api_key_env} not set (needed for provider '{self.provider}')")
        return instructor.from_openai(
            OpenAI(base_url=base, api_key=key, max_retries=6, timeout=90.0),
            mode=instructor.Mode.JSON_SCHEMA)

    def failure_rate(self) -> float:
        with self._lock:
            return self.failures / self.calls if self.calls else 0.0

    def _cache_key(self, system: str, user: str, model_cls: type, temperature: float) -> str:
        blob = json.dumps([self.provider, self.model, self.seed, temperature, model_cls.__name__,
                           model_cls.model_json_schema(), system, user], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def chat_json(self, system: str, user: str, response_model: type[BaseModel],
                  temperature: float = 0.8, max_tokens: int = 1536) -> Any:
        """Return a validated `response_model` as a plain dict (`.model_dump()`), or `{}` on failure.
        Degrades gracefully — one flaky response yields 0 examples for that job, counted so the driver
        can abort loudly if the aggregate failure rate is high. `max_tokens` must be generous enough
        for the largest coupled/nested outputs (multi-pair PAIRS, batched CATALOG); too low truncates
        mid-JSON -> IncompleteOutputException -> 0 examples for that job."""
        with self._lock:
            self.calls += 1
        key = self._cache_key(system, user, response_model, temperature) if self._cache is not None else None
        if key is not None and key in self._cache:
            return self._cache[key]
        try:
            obj = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_model=response_model,
                temperature=temperature,
                seed=self.seed,
                max_tokens=max_tokens,
                max_retries=3,  # instructor re-asks on a validation miss
            )
            out = obj.model_dump()
            if key is not None:
                self._cache[key] = out
            return out
        except Exception as e:  # noqa: BLE001 — a single bad response must not kill a multi-hour run
            with self._lock:
                self.failures += 1
            print(f"[teacher] chat_json gave up ({type(e).__name__}: {str(e)[:80]}); skipping one job")
            return {}

    def verify_grounded(self, question: str, results_block: str, answer: str) -> bool:
        """Faithfulness gate: does the ANSWER stay grounded in the RESULTS (no invented fact/number/
        name/capability)? Fail-OPEN on verifier error — only a confident 'no' rejects. Counts as a
        normal call so its failures show in the health gate."""
        sysmsg = ("You are a STRICT grounding auditor for a shopping assistant. Given SEARCH RESULTS "
                  "and an ANSWER, FIRST list every factual claim in the answer (product names, prices, "
                  "numbers, materials, specs, features, warranties, capabilities) that is NOT explicitly "
                  "stated in the results; THEN set supported=true ONLY if that list is empty. Paraphrase "
                  "and reasonable summary are fine; any NEW fact is unsupported. An honest 'I don't have "
                  "that information' is fully supported (empty list).")
        user = f"SEARCH RESULTS:\n{results_block}\n\nQUESTION: {question}\n\nANSWER: {answer}"
        out = self.chat_json(sysmsg, user, GroundingVerdict, temperature=0.0)
        ok = bool(out.get("supported", True)) if isinstance(out, dict) else True
        if not ok:  # track rejections so a too-strict verifier hollowing recipes is VISIBLE, not silent
            with self._lock:
                self.rejections += 1
        return ok

    def parallel_map(self, fn: Callable, jobs: Iterable) -> list:
        def safe(x):
            try:
                return fn(x)
            except Exception as e:  # noqa: BLE001 — one bad job never kills the whole run
                print(f"[teacher] job failed, skipping: {type(e).__name__}: {str(e)[:100]}")
                return []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(safe, jobs))
