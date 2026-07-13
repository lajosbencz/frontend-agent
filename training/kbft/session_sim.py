"""Semi-random session simulator — compose multi-turn conversations from guarded 'moves' over an
authoritative world-state, instead of one fixed shape per recipe.

Design (after APIGen-MT / STATEGEN / agenda-based user simulators):
  - WORLD-STATE is truth (STATEGEN 'backend-is-truth'): tools read/write a running state (cart, last
    search results, seen ids, browsed items), so every move is grounded/consistent BY CONSTRUCTION —
    an add can only use an id a prior search surfaced; you can't check out an empty cart.
  - A sampled GOAL/AGENDA (agenda-based simulators) gives coherence: the walk is semi-random but
    driven toward a small stack of target intents, interleaved with realistic noise.
  - STRUCTURE is deterministic; the teacher writes only the NL surface — the same split kbft already
    uses, which is also APIGen-MT's decouple-blueprint-from-dialogue principle.

Guards encode the tool-dependency graph (add needs a prior result; checkout/view need a cart). Moves
reuse the recipe primitives (`_query_from`, `_ent_result`, `ctx.call/multi_call`, …) so behaviour
stays identical to the standalone recipes — only the composition is new.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from kbft.generic_gen import (A_ONE, Q_ONE, PackCtx, _batch_searches, _DECISIVE, _ent_result,
                              _query_from, _results_block, _verified)
from kbft.schema import Entity, Example
from kbft.turns import a, tool_result, u

OFF_TOPIC = ["the weather", "flight bookings", "stock tips", "a hotel room", "legal advice"]


@dataclass
class SessionSim:
    """One shopping session as a walk over a shared world-state. `run()` returns an Example or None."""

    ctx: PackCtx
    rng: random.Random
    turns: list = field(default_factory=list)
    cart: list = field(default_factory=list)          # [{id,title,price,qty}]
    last_results: list = field(default_factory=list)   # most recent search results (reference target)
    seen_ids: set = field(default_factory=set)         # every id any search has surfaced (grounding)
    browsed: list = field(default_factory=list)        # entities currently on screen

    def __post_init__(self):
        self.by_id = self.ctx.kb.by_id()

    # --- teacher surface (deterministic structure stays in the moves) ---
    def ask(self, prompt: str, temp: float = 0.95) -> str | None:
        o = self.ctx.cfg.teacher.chat_json(self.ctx.gsys, prompt, Q_ONE, temperature=temp)
        return o["question"] if isinstance(o, dict) and o.get("question") else None

    def reply(self, prompt: str, temp: float = 0.7) -> str | None:
        o = self.ctx.cfg.teacher.chat_json(self.ctx.gsys, prompt, A_ONE, temperature=temp)
        return o["answer"] if isinstance(o, dict) and o.get("answer") else None

    def _record(self, res: list[dict]):
        self.last_results = res
        self.seen_ids |= {r["id"] for r in res}
        self.browsed = [self.by_id[r["id"]] for r in res if r["id"] in self.by_id]

    # ================= MOVES: each emits turns + mutates state; returns True on success =============
    def m_browse(self) -> bool:
        groups: dict[str, list[Entity]] = {}
        for e in self.ctx.kb.entities:
            groups.setdefault(e.group, []).append(e)
        group = self.rng.choice(list(groups))
        q = group
        res = self.ctx.retr.search_catalog(q, k=5)
        ids = {r["id"] for r in res}
        for e in groups[group][:3]:  # gold-present safety net
            if e.id not in ids:
                res = [_ent_result(e), *res]
        res = res[:5]
        qt = self.ask(f"The customer wants to browse the '{group}' category. Write ONE short, casual "
                      f"request to see what's on offer.")
        if not qt:
            return False
        self.turns += [u(qt), self.ctx.call("search_catalog", query=q), tool_result({"results": res})]
        self.turns.append(a(self.ctx.loc.t("options", listing="; ".join(r["title"] for r in res[:4]))))
        self._record(res)
        return True

    def m_add_reference(self) -> bool:
        cands = [(i, r) for i, r in enumerate(self.last_results[:3])
                 if (e := self.by_id.get(r["id"])) and e.in_stock]
        if not cands:
            return False
        idx, r = self.rng.choice(cands)
        e = self.by_id[r["id"]]
        ordn = self.ctx.loc.ordinal(idx) if idx < len(self.ctx.loc.ordinals) else "that one"
        qt = self.ask(f"The customer just saw a list and wants the {ordn} item ('{e.title}'). Write ONE "
                      f"short request to add it, referring to it by POSITION (not its full name).")
        if not qt:
            return False
        self.turns += [u(qt), self.ctx.call("add_to_cart", id=e.id, quantity=1),
                       tool_result({"ok": True, "added": {"id": e.id, "title": e.title}})]
        self.cart.append({"id": e.id, "title": e.title, "price": e.price, "qty": 1})
        self.turns.append(a(self.ctx.loc.t("added", title=e.title)))
        return True

    def m_batch_add(self) -> bool:
        pool = [e for e in self.ctx.kb.entities if e.in_stock]
        if len(pool) < 2:
            return False
        items = self.rng.sample(pool, 2)
        qt = self.ask(f"The customer wants BOTH of these at once: '{items[0].title}' and "
                      f"'{items[1].title}'. Write ONE natural request for both.")
        if not qt:
            return False
        searches, results, _ = _batch_searches(self.ctx, items)
        self.turns += [u(qt), self.ctx.multi_call(*searches), *results,
                       self.ctx.multi_call(*[("add_to_cart", {"id": it.id, "quantity": 1}) for it in items]),
                       *[tool_result({"ok": True, "added": {"id": it.id, "title": it.title}}) for it in items]]
        for it in items:
            self.cart.append({"id": it.id, "title": it.title, "price": it.price, "qty": 1})
            self.seen_ids.add(it.id)
        self.turns.append(a(self.ctx.loc.t("added_both", a=items[0].title, b=items[1].title)))
        return True

    def m_ask_kb(self) -> bool:
        docs = self.ctx.kb.docs
        if not docs:
            return False
        doc = self.rng.choice(docs)
        qt = self.ask(f"Article '{doc.title}':\n{doc.body[:600]}\n\nWrite ONE natural how-to/policy "
                      f"question answerable from this article.")
        if not qt:
            return False
        res = self.ctx.retr.search_knowledge(_query_from(qt), k=4)
        if not any(r["id"] == doc.id for r in res):
            res = [{"id": doc.id, "title": doc.title, "snippet": doc.body[:200], "score": 1.0}, *res[:3]]
        ans = self.reply(f"Knowledge results:\n{_results_block(res)}\n\nAnswer using ONLY these results, "
                         f"concisely.\nQuestion: {qt}" + _DECISIVE)
        if not ans or not _verified(self.ctx, qt, res, ans):
            return False
        self.turns += [u(qt), self.ctx.call("search_knowledge", query=_query_from(qt)),
                       tool_result({"results": res}), a(ans)]
        self._record(res)
        return True

    def m_view_cart(self) -> bool:
        total = round(sum(c["price"] * c["qty"] for c in self.cart if c["price"]), 2)
        view = {"cart": [{"id": c["id"], "title": c["title"], "price": c["price"], "quantity": c["qty"]}
                         for c in self.cart], "total": total}
        qt = self.ask("The customer wants to see what's in their cart. Write ONE short request.")
        if not qt:
            return False
        self.turns += [u(qt), self.ctx.call("view_cart"), tool_result(view)]
        if len(self.cart) == 1:
            c = self.cart[0]
            self.turns.append(a(self.ctx.loc.t("cart_one", title=c["title"],
                                               price=self.ctx.loc.money(c["price"]),
                                               total=self.ctx.loc.money(total))))
        else:
            self.turns.append(a(self.ctx.loc.t("options", listing="; ".join(c["title"] for c in self.cart))))
        return True

    def m_checkout(self) -> bool:
        qt = self.ask("The customer is done and wants to check out. Write ONE short request.")
        if not qt:
            return False
        self.turns += [u(qt), self.ctx.call("navigate", target="checkout"),
                       tool_result({"ok": True, "navigated": "checkout"}),
                       a(self.ctx.loc.t("nav_payment"))]
        return True

    def m_refuse_offtopic(self) -> bool:
        topic = self.rng.choice(OFF_TOPIC)
        qt = self.ask(f"The customer asks about {topic} — something this store does NOT handle. Write "
                      f"ONE natural off-topic request.")
        if not qt:
            return False
        self.turns += [u(qt), a(self.ctx.loc.t("not_carry", term=topic, tail=""))]
        return True

    # ================= WALK: goal-directed, semi-random, guarded ===================================
    MOVES = [
        # (method, guard(sim)->bool, weight). Guards encode the tool-dependency graph.
        ("m_browse",         lambda s: True,                     3.0),
        ("m_ask_kb",         lambda s: bool(s.ctx.kb.docs),      2.0),
        ("m_add_reference",  lambda s: bool(s.last_results),     3.0),
        ("m_batch_add",      lambda s: True,                     1.5),
        ("m_view_cart",      lambda s: bool(s.cart),             1.0),
        ("m_refuse_offtopic", lambda s: True,                    0.7),
    ]

    def run(self) -> Example | None:
        # Agenda: an opener that populates results, then a longer semi-random walk (so a session
        # amortizes the fixed system-prompt/catalog cost across many turns), then maybe checkout.
        # Length isn't token-targeted here — the render-time guard warns against the config max_len.
        opener = self.rng.choice(["m_browse", "m_ask_kb"])
        getattr(self, opener)()
        for _ in range(self.rng.randint(3, 8)):
            eligible = [(n, w) for n, g, w in self.MOVES if g(self)]
            names, weights = zip(*eligible)
            getattr(self, self.rng.choices(names, weights=weights)[0])()
        if self.cart and self.rng.random() < 0.5:
            self.m_checkout()
        # need at least one real user turn to be a usable example
        return Example(self.ctx.system(), self.turns) if self.turns else None


def simulate_sessions(ctx: PackCtx, n: int, seed: int) -> list[Example]:
    """Generate `n` composed sessions for a pack (used by generate_generic behind --sessions).

    Deterministic/reproducible: each session gets its OWN rng seeded from a stable string
    (seed, pack, index) — never the shared ctx.rng — so thread scheduling can't change the output and
    a re-run with the same seed is byte-identical (teacher surface reproduces via its own seed+cache)."""
    slug = ctx.pack.get("slug", "?")

    def job(i):
        rng = random.Random(f"session:{seed}:{slug}:{i}")
        ex = SessionSim(ctx, rng).run()
        return [ex] if ex else []

    return [e for sub in ctx.cfg.teacher.parallel_map(job, range(n)) for e in sub]
