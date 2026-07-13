"""Replay a fixed chat stream against a GGUF — a faithful headless reproduction of the demo.

Same contract AND same data as the browser demo: the trained system prompt (persona + catalog hint +
tool list), the GBNF grammar with id-grounding per turn, and retrieval over the demo's shipped index
(`demo/public/rag/index.json`) with light stemming (mirrors the demo's minisearch+Porter). Prints the
stream and asserts the expected behaviour, so a bad quant/version is caught on the real acceptance flow.

Usage:
  uv run python scripts/replay_chat.py --gguf artifacts/gguf/publish/lfm2.5-230m-frontend-agent-v1.0.0-Q6_K.gguf
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from transformers import AutoTokenizer

from kbft.gbnf import build_tool_grammar
from kbft.gguf_runtime import pick_backend, serve
from kbft.toolcall import STOP, parse_calls
from kbft.tools import GENERIC_TOOLS
from kbft.turns import a, call, tool_result, u

DEMO_INDEX = REPO.parent / "demo" / "public" / "rag" / "index.json"

# Byte-identical to the trained persona (store = BrewCraft, vertical = espresso equipment).
PERSONA = (
    "You are the shopping assistant for BrewCraft, an online espresso equipment store. Use the tools "
    "to search the catalog and the knowledge base and to manage the cart. For a product's price or "
    "availability (whether it is in stock), search the catalog; for how-to, care, and policies, search "
    "the knowledge base. Ground every answer ONLY in what the tools return; if a search returns nothing "
    "relevant, say you don't have that information rather than guessing. Never state a product's price "
    "or whether it is in stock unless a catalog result says so. When the user asks to add or find a "
    "specific item, search the catalog for THAT item first and act on the matching result. Only add "
    "items to the cart when the user asks. Use the exact item id from search results when calling cart tools."
)

# Tool description overrides: make search_catalog own price+availability and search_knowledge clearly
# guides/policies (the trained descriptions were ambiguous — "product info" pulled stock queries to
# the knowledge base). The model reads the injected schema, so clearer descriptions fix routing.
_DESCRIPTIONS = {
    "search_catalog": "Full-text search the product catalog. Returns matching items with their id, "
    "title, price, availability (in stock or not), and a short snippet. Use it for products, prices, "
    "and stock/availability.",
    "search_knowledge": "Full-text search the knowledge base: buying guides, how-to, care, and "
    "policies. Use it for how-to and policy questions — not for prices or stock.",
}

# The acceptance flow the demo must handle well (the user's example + the stock-grounding case), in a
# natural order (add before the unrelated stock question — interleaving them is adversarial for a 230M).
DEFAULT_CONVO = [
    "how do i descale?",
    "what types of machines do you offer?",
    "add a descaler to my cart",
    "are cleaning tablets in stock?",
    "take me to checkout",
]


def _tools() -> list[dict]:
    import copy
    ts = copy.deepcopy(GENERIC_TOOLS)
    for t in ts:
        fn = t.get("function", t)
        if fn["name"] in _DESCRIPTIONS:
            fn["description"] = _DESCRIPTIONS[fn["name"]]
    return ts


TOOLS = _tools()


def _stem(w: str) -> str:
    w = w.lower()
    for suf in ("ing", "ers", "er", "es", "ed", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def _toks(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower())]


class DemoRAG:
    """Light BM25-ish retrieval over the demo's shipped index — mirrors the demo's minisearch."""

    def __init__(self, path: Path):
        idx = json.loads(path.read_text())
        self.catalog = idx["catalog"]
        self.knowledge = idx["knowledge"]
        self.by_id = {c["id"]: c for c in self.catalog}
        # (title tokens, body tokens) — title matches are boosted, mirroring minisearch boost:{title:2}
        self._cat = {c["id"]: (set(_toks(c["title"])), set(_toks(f"{c.get('group','')} {c.get('summary','')}")))
                     for c in self.catalog}
        self._kn = {d["id"]: (set(_toks(d["title"])), set(_toks(d.get("text", "")))) for d in self.knowledge}

    def _rank(self, query: str, toks_by_id: dict[str, tuple[set, set]]) -> list[tuple[str, float]]:
        q = set(_toks(query))
        scored = [(cid, 2.0 * len(q & title) + len(q & body)) for cid, (title, body) in toks_by_id.items()]
        return sorted([(c, s) for c, s in scored if s > 0], key=lambda x: -x[1])

    def search_catalog(self, query: str, k: int = 5, max_price=None) -> list[dict]:
        out = []
        for cid, score in self._rank(query, self._cat):
            c = self.by_id[cid]
            if max_price is not None and (c["price"] is None or c["price"] > max_price):
                continue
            out.append({"id": c["id"], "title": c["title"], "snippet": (c.get("summary") or "")[:120],
                        "price": c["price"], "in_stock": c["in_stock"], "attrs": {}, "score": float(score)})
            if len(out) >= k:
                break
        return out

    def search_knowledge(self, query: str, k: int = 4) -> list[dict]:
        km = {d["id"]: d for d in self.knowledge}
        out = []
        for did, score in self._rank(query, self._kn):
            d = km[did]
            out.append({"id": d["id"], "title": d["title"], "snippet": (d.get("text") or "")[:480],
                        "score": float(score)})
            if len(out) >= k:
                break
        return out

    def hint(self, n: int = 6) -> str:
        # representative sample across groups (round-robin), mirroring the library's LocalMiniSearchRAG
        buckets: dict[str, list] = {}
        for c in self.catalog:
            buckets.setdefault(c.get("group", ""), []).append(c)
        cols = list(buckets.values())
        picked = []
        for i in range(max((len(b) for b in cols), default=0)):
            for b in cols:
                if i < len(b):
                    picked.append(b[i])
                if len(picked) >= n:
                    break
            if len(picked) >= n:
                break
        return "; ".join(f"{c['title']} [{c['id']}]" for c in picked)


def replay(gguf: str, convo: list[str], grammar_on: bool) -> list[dict]:
    rag = DemoRAG(DEMO_INDEX)
    tok = AutoTokenizer.from_pretrained("LiquidAI/LFM2.5-230M")
    system = f"{PERSONA}\n\nExample catalog items: {rag.hint(6)}"
    messages: list[dict] = []
    cart: list[dict] = []
    seen_ids: list[str] = []
    turns: list[dict] = []
    ngl = pick_backend(gguf, prefer_gpu=True)

    def dispatch(name: str, args: dict) -> dict:
        if name == "search_catalog":
            res = rag.search_catalog(args.get("query", ""), max_price=args.get("max_price"))
            seen_ids.extend(r["id"] for r in res)
            return {"results": res}
        if name == "search_knowledge":
            res = rag.search_knowledge(args.get("query", ""))
            seen_ids.extend(r["id"] for r in res)
            return {"results": res}
        if name == "add_to_cart":
            c = rag.by_id.get(args.get("id"))
            if c is None:
                return {"error": "not_found", "id": args.get("id")}
            if not c["in_stock"]:
                return {"error": "out_of_stock", "id": c["id"]}
            qty = int(args.get("quantity", 1) or 1)
            cart.append({"id": c["id"], "title": c["title"], "price": c["price"], "quantity": qty})
            return {"ok": True, "added": {"id": c["id"], "title": c["title"], "quantity": qty}}
        if name == "remove_from_cart":
            args_id = args.get("id")
            cart[:] = [x for x in cart if x["id"] != args_id]
            return {"ok": True, "removed": args_id}
        if name == "view_cart":
            return {"cart": cart, "total": round(sum(x["price"] * x["quantity"] for x in cart if x["price"]), 2)}
        if name == "clear_cart":
            cart.clear()
            return {"ok": True, "cleared": True}
        if name == "navigate":
            target = str(args.get("target", "")).lower()
            if target not in {"checkout", "cart", "home", "product"}:
                return {"error": "unknown_target", "target": target}
            return {"ok": True, "navigated": target}
        return {"error": "unknown_tool", "name": name}

    with serve(gguf, n_gpu_layers=ngl) as srv:
        for user_msg in convo:
            messages.append(u(user_msg))
            print(f"\n\033[1m{user_msg}\033[0m")
            turn = {"user": user_msg, "calls": [], "final": ""}
            for _ in range(8):
                prompt = tok.apply_chat_template(
                    [{"role": "system", "content": system}] + messages,
                    tools=TOOLS, add_generation_prompt=True, tokenize=False)
                grammar = build_tool_grammar(TOOLS, seen_ids or None) if grammar_on else None
                gen = srv.complete(prompt, n_predict=220, stop=STOP, grammar=grammar)
                emitted = parse_calls(gen)
                if not emitted:
                    final = re.sub(r"<\|.*?\|>", "", gen).strip()
                    turn["final"] = final
                    messages.append(a(final))
                    print(f"  {final}")
                    break
                for name, args in emitted:
                    res = dispatch(name, args)
                    turn["calls"].append({"name": name, "args": args, "result": res})
                    messages.append(call(name, args))
                    messages.append(tool_result(res))
                    n = len(res["results"]) if isinstance(res, dict) and "results" in res else None
                    tail = f"{n} results" if n is not None else json.dumps(res)[:70]
                    print(f"  \033[36m→ {name}({json.dumps(args)})\033[0m  {tail}")
            turns.append(turn)
    return turns


def _names(turn: dict) -> list[str]:
    return [c["name"] for c in turn["calls"]]


def _turn(turns: list[dict], *keys: str) -> dict:
    return next(t for t in turns if all(k in t["user"].lower() for k in keys))


def check(turns: list[dict]) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []
    descale, machines = _turn(turns, "descale"), _turn(turns, "machines")
    stock, add, checkout = _turn(turns, "stock"), _turn(turns, "add"), _turn(turns, "checkout")

    out.append(("descale → search_knowledge", "search_knowledge" in _names(descale), str(_names(descale))))
    out.append(("descale answer grounded", bool(re.search(r"descal|rins|water|run|flush", descale["final"], re.I)),
                descale["final"][:70]))

    q = next((c["args"].get("query", "") for c in machines["calls"] if c["name"] == "search_catalog"), "")
    out.append(("machines → search_catalog", "search_catalog" in _names(machines), str(_names(machines))))
    out.append(("machines query sensible (not 'beverages')", bool(q) and "beverage" not in q.lower(),
                f"query={q!r}"))
    out.append(("machines answer lists items", len(machines["final"]) > 10 and
                not re.search(r"no .*available|don't have that", machines["final"], re.I), machines["final"][:70]))

    # stock query MUST route to the catalog (not the knowledge base) and report OUT of stock (it is).
    out.append(("stock → search_catalog (not search_knowledge)",
                "search_catalog" in _names(stock) and "search_knowledge" not in _names(stock), str(_names(stock))))
    out.append(("stock answer grounded (says NOT in stock)",
                bool(re.search(r"not .*stock|out of stock|unavailable|isn't|is not", stock["final"], re.I)),
                stock["final"][:80]))

    adds = [c for c in add["calls"] if c["name"] == "add_to_cart"]
    added_titles = " ".join(a["result"].get("added", {}).get("title", "") for a in adds if a["result"].get("ok"))
    out.append(("add descaler → grounded add of an actual descaler",
                bool(adds) and all(a["result"].get("ok") for a in adds) and "descal" in added_titles.lower(),
                str([a["result"].get("added") or a["result"] for a in adds])))
    out.append(("checkout → navigate(checkout)",
                any(c["name"] == "navigate" and str(c["args"].get("target")).lower() == "checkout"
                    for c in checkout["calls"]), str([c["args"] for c in checkout["calls"]])))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", required=True)
    ap.add_argument("--no-grammar", action="store_true", help="disable GBNF (demo uses it; on by default)")
    args = ap.parse_args()
    turns = replay(args.gguf, DEFAULT_CONVO, grammar_on=not args.no_grammar)
    checks = check(turns)
    print("\n\033[1m=== assertions ===\033[0m")
    passed = sum(ok for _, ok, _ in checks)
    for label, ok, detail in checks:
        mark = "\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m"
        print(f"  {mark} {label}" + ("" if ok else f"   [{detail}]"))
    print(f"\n{passed}/{len(checks)} passed")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
