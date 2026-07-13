"""Teacher reframing: raw fact-seed packs -> clean packs.

Raw Amazon meta is SEO/marketing soup (keyword stuffing, shipping notes, inconsistent casing).
Grounding search_knowledge on that teaches the model to ground on garbage. So we apply the project's
core rule to the KB itself: real facts in, teacher-written surface out. The teacher rewrites each
item's messy text into clean, neutral product copy + a one-line blurb, GROUNDED STRICTLY to the
supplied details (forbidden to invent specs, numbers, or brands — the failure mode small models fall
into). Facts that stay authoritative (title, brand, category, price) come from the raw pack, not the
teacher.

This is the same teacher path as synthesis (kbft synth for exotic verticals): reframe =
rewrite-from-seed, synthesize = author-from-nothing; both yield uniform clean packs.
"""

from __future__ import annotations

from pydantic import BaseModel

from kbft.teacher import Teacher

REFRAME_SYS = (
    "You write clean, neutral e-commerce product copy. Use ONLY the details provided; never invent "
    "specifications, numbers, brands, materials, or features that are not present in the source. No "
    "marketing hype, no shipping/packaging/warranty notes, no ALL-CAPS. If the source is thin, keep "
    "it short rather than padding."
)

class REFRAME_SCHEMA(BaseModel):
    blurb: str = ""              # one concise sentence (catalog summary)
    description: str = ""        # 2-3 clean sentences of product copy
    specs: list[str] = []        # "key: value", from source only


def _user(title: str, brand: str, group: str, raw: str) -> str:
    lines = [f"Product title: {title}", f"Category: {group}"]
    if brand:
        lines.append(f"Brand: {brand}")
    lines.append(f"Source details (messy): {raw[:700]}")
    lines.append("\nWrite a clean catalog entry for this product.")
    return "\n".join(lines)


def reframe_pack(pack: dict, teacher: Teacher, temperature: float = 0.4) -> dict:
    """Return a clean copy of `pack`: entities gain a teacher blurb summary, docs get clean bodies.
    Facts (id/title/group/price/attrs) are preserved verbatim from the raw pack."""
    raw_body = {d["id"]: d.get("body", "") for d in pack.get("docs", [])}

    def do(e: dict) -> dict:
        raw = raw_body.get(f"{e['id']}-doc", "")
        out = teacher.chat_json(
            REFRAME_SYS,
            _user(e["title"], (e.get("attrs") or {}).get("brand", ""), e.get("group", ""), raw),
            REFRAME_SCHEMA, temperature=temperature)
        blurb = (out.get("blurb") or "").strip() if isinstance(out, dict) else ""
        desc = (out.get("description") or "").strip() if isinstance(out, dict) else ""
        specs = [s.strip() for s in (out.get("specs") or []) if isinstance(s, str) and s.strip()] \
            if isinstance(out, dict) else []
        if not desc:  # teacher failed on this item — keep it, degrade to a trimmed raw sentence
            desc = raw[:200].rsplit(".", 1)[0].strip() or e["title"]
        body = desc if not specs else desc + "\n" + "\n".join(f"- {s}" for s in specs[:6])
        clean_e = {k: e[k] for k in ("id", "title", "group", "price", "attrs") if k in e}
        clean_e["summary"] = blurb or desc[:120]
        return {"entity": clean_e, "doc": {"id": f"{e['id']}-doc", "title": e["title"], "body": body}}

    results = teacher.parallel_map(do, pack["entities"])
    results = [r for r in results if isinstance(r, dict) and r.get("entity")]
    return {
        "slug": pack["slug"],
        "vertical": pack.get("vertical", pack["slug"]),
        "store_name": pack.get("store_name", ""),
        "entities": [r["entity"] for r in results],
        "docs": [r["doc"] for r in results],
    }
