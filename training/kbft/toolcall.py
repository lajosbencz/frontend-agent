"""Parse and execute LFM2.5 pythonic tool calls — the decode side of the tool contract.

`kbft/gbnf.py` constrains the model to emit `[name(k='v')]`; this reads that back and runs it
deterministically against a pack's retriever + cart, mirroring the frozen training result shapes.
Shared by the eval harness, the live probe, and the demo replay.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kbft.generic_gen import PackCtx

# A tool-call turn is a pythonic call list at the START of the generation. The <|tool_call_start|>/
# <|tool_call_end|> markers are SPECIAL tokens that llama-server strips from /completion text, so the
# model's tool call arrives as a bare `[fn(args)]`. Both markers are therefore optional; we anchor at
# the output start so a bracketed list inside a prose answer can't be mistaken for a call (and
# parse_calls further requires a `name(...)` inside, so prose never matches).
BLOCK_RE = re.compile(r"^\s*(?:<\|tool_call_start\|>\s*)?\[(.*?)\]", re.DOTALL)
CALL_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.]*)\s*\((.*?)\)", re.DOTALL)
KW_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
                   r"(\"[^\"]*\"|'[^']*'|-?\d+\.\d+|-?\d+|True|False|None)")
STOP = ["<|im_end|>"]  # NOT <|tool_call_end|> — server strips stops, which would drop the block close


def _coerce(v: str):
    if v[:1] in "\"'":
        return v[1:-1]
    if v in ("True", "False"):
        return v == "True"
    if v == "None":
        return None
    return float(v) if "." in v else int(v)


def parse_calls(text: str) -> list[tuple[str, dict]]:
    """Return [(emitted_name, {emitted_arg: value})] from the first tool-call block, or []."""
    m = BLOCK_RE.search(text)
    if not m:
        return []
    calls = []
    for name, inner in CALL_RE.findall(m.group(1)):
        args = {k: _coerce(v) for k, v in KW_RE.findall(inner)}
        calls.append((name, args))
    return calls


class ToolExec:
    """Executes canonical tool calls against a PackCtx's retriever + a live cart."""

    def __init__(self, ctx: PackCtx):
        self.ctx = ctx
        self.by_id = ctx.kb.by_id()
        self.cart: list[dict] = []
        self.search_ids: list[str] = []      # every id ever returned by a search (for grounding)
        self.last_results: list[dict] = []    # most recent search results (for reference tracking)

    def run(self, canon: str, args: dict) -> dict:
        if canon == "search_catalog":
            res = self.ctx.retr.search_catalog(args.get("query", ""), k=4,
                                                max_price=args.get("max_price"))
            self.last_results = res
            self.search_ids += [r["id"] for r in res]
            return {"results": res}
        if canon == "search_knowledge":
            res = self.ctx.retr.search_knowledge(args.get("query", ""), k=4)
            self.last_results = res
            self.search_ids += [r["id"] for r in res]
            return {"results": res}
        if canon == "add_to_cart":
            eid, qty = args.get("id"), int(args.get("quantity", 1) or 1)
            e = self.by_id.get(eid)
            if e is None:
                return {"ok": False, "error": "unknown id"}
            if not e.in_stock:
                return {"ok": False, "error": "out of stock"}
            self.cart.append({"id": eid, "title": e.title, "price": e.price, "quantity": qty})
            return {"ok": True, "added": {"id": eid, "title": e.title, "quantity": qty}}
        if canon == "remove_from_cart":
            eid = args.get("id")
            self.cart = [c for c in self.cart if c["id"] != eid]
            return {"ok": True, "removed": eid}
        if canon == "view_cart":
            return {"cart": self.cart, "total": round(sum(c["price"] * c["quantity"]
                                                          for c in self.cart if c["price"]), 2)}
        if canon == "clear_cart":
            self.cart = []
            return {"ok": True, "cleared": True}
        if canon == "submit_form":
            fields = {k: args.get(k) for k in ("form", "name", "email", "subject", "message")
                      if args.get(k) is not None}
            return {"ok": True, "submitted": fields}
        return {"ok": False, "error": "unknown tool"}
