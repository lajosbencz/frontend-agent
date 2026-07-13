"""Generation-time retriever — the ground-truth source for RAG recipes.

PARAMOUNT (see docs/base-training-procedure.md §7a): every grounded training answer is produced from
what THIS retriever returns, never from the full KB. It is a stand-in for the deployment RAG endpoint
(the demo's SurrealDB BM25), so training matches inference: at runtime the model likewise only sees
`search_*` tool results. BM25 over the pack keeps the stand-in faithful to a real fulltext backend.

Returns the frozen model-facing result shape:
  search_knowledge(q) -> [{id, title, snippet, score}]
  search_catalog(q)   -> [{id, title, snippet, price, attrs, score}]
"""

from __future__ import annotations

import math
import re
from collections import Counter

from kbft.schema import KB

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def _snippet(text: str, cap: int = 160) -> str:
    text = (text or "").strip()
    return text[:cap].rstrip()


class _BM25:
    """Minimal BM25 over a list of (id, searchable_text, payload) records."""

    def __init__(self, records: list[tuple[str, str, dict]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [{"id": rid, "payload": pl, "tf": Counter(tokenize(txt)),
                      "len": len(tokenize(txt))} for rid, txt, pl in records]
        self.avglen = (sum(d["len"] for d in self.docs) / len(self.docs)) if self.docs else 0.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d["tf"].keys())
        n = len(self.docs)
        # BM25+ idf (never negative), so common terms just contribute little rather than penalizing
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, k: int) -> list[tuple[dict, float]]:
        q = tokenize(query)
        if not q or not self.docs:
            return []
        scored = []
        for d in self.docs:
            score = 0.0
            for t in q:
                tf = d["tf"].get(t)
                if not tf:
                    continue
                idf = self.idf.get(t, 0.0)
                denom = tf + self.k1 * (1 - self.b + self.b * d["len"] / (self.avglen or 1))
                score += idf * (tf * (self.k1 + 1)) / denom
            if score > 0:
                scored.append((d, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(d["payload"], s) for d, s in scored[:k]]


class PackRetriever:
    def __init__(self, kb: KB):
        self._know = _BM25([
            (d.id, f"{d.title} {d.body}", {"id": d.id, "title": d.title, "body": d.body})
            for d in kb.docs
        ])
        self._cat = _BM25([
            (e.id, f"{e.title} {e.group} {e.summary}",
             {"id": e.id, "title": e.title, "summary": e.summary, "group": e.group,
              "price": e.price, "in_stock": e.in_stock, "attrs": e.attrs})
            for e in kb.entities
        ])

    def search_knowledge(self, query: str, k: int = 4, min_score: float = 0.0) -> list[dict]:
        # Knowledge snippets are long (480) so procedural/how-to answers (e.g. descaling steps) are
        # actually PRESENT in the result — a 160-char snippet cut the steps off and forced refusals.
        return [{"id": p["id"], "title": p["title"], "snippet": _snippet(p["body"], 480),
                 "score": round(s, 3)} for p, s in self._know.search(query, k) if s >= min_score]

    def search_catalog(self, query: str, k: int = 5, max_price: float | None = None,
                       min_score: float = 0.0) -> list[dict]:
        hits = self._cat.search(query, k * 3 if max_price else k)
        out = []
        for p, s in hits:
            if s < min_score:
                continue
            if max_price is not None and (p["price"] is None or p["price"] > max_price):
                continue
            out.append({"id": p["id"], "title": p["title"], "snippet": _snippet(p["summary"], 120),
                        "price": p["price"], "in_stock": p["in_stock"], "attrs": p["attrs"],
                        "score": round(s, 3)})
            if len(out) >= k:
                break
        return out
