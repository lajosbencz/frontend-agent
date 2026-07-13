"""Teacher-synthesized packs for verticals HF lacks (crypto, movies, portfolios, SaaS, tickets…).

Unlike reframing (real facts in, clean surface out), synthesis INVENTS a fictional store: the teacher
authors a self-consistent catalog + KB from scratch. Because the store is fictional, there's no
external ground truth to violate — the failure mode is internal INCONSISTENCY (a description that
contradicts the item), not hallucination of real facts. So the constraint here is: original,
plausible, internally consistent; no real brands or copyrighted titles.

Output is the same clean pack shape the reframer produces, so it drops straight into data/packs/ and
is treated identically by the generic generator. No reframe pass needed (already clean).
"""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel

from kbft.locales import Locale, get_locale
from kbft.teacher import Teacher

SYNTH_SYS = (
    "You invent realistic, self-consistent catalogs for a fictional online store. Every item must be "
    "plausible and internally consistent — the description must match the item's name, category, and "
    "price. Invent ORIGINAL names; never use real brands, real companies, or copyrighted titles. No "
    "marketing hype."
)

class _CatalogItem(BaseModel):
    name: str
    category: str
    price: float
    description: str
    blurb: str = ""  # one-line catalog summary (optional)


class CATALOG_SCHEMA(BaseModel):
    items: list[_CatalogItem] = []


def _items(out) -> list[dict]:
    items = out.get("items", []) if isinstance(out, dict) else (out if isinstance(out, list) else [])
    return [x for x in items if isinstance(x, dict) and x.get("name") and x.get("description")]


class _Article(BaseModel):
    title: str
    body: str


# Generic KB article types (any vertical) so packs carry real how-to/policy/guide content — not just
# per-item descriptions — matching the demo's rich guide-based KB the rag/kb patterns must generalize to.
_KB_TOPICS = [
    ("Getting Started", "a friendly beginner's guide to choosing and using {v} products"),
    ("Buying Guide", "how to choose among the {c} categories and which suits which customer"),
    ("Care and Usage", "how to get the most from and look after purchases from this store"),
    ("Category Comparison", "how the {c} categories differ, with concrete examples"),
    ("Shipping and Returns", "this store's shipping, returns, and warranty policy (invent reasonable terms)"),
    ("FAQ", "the most common customer questions for this store, each with a concrete answer"),
]


def _synth_docs(spec: dict, teacher, loc) -> list[dict]:
    """Invent a handful of KB guide/policy articles for the pack (grounded in the vertical)."""
    sysmsg = SYNTH_SYS + loc.synth_sys_suffix()
    v, c = spec["vertical"], ", ".join(spec["categories"])
    docs = []
    for title, brief in _KB_TOPICS:
        prompt = (f"Store: {spec['store_name']} — {spec['brief']}\nCategories: {c}.{loc.synth_prompt_line()}\n"
                  f"Write a knowledge-base article titled '{title}': {brief.format(v=v, c=c)}. Use 3-5 "
                  f"short paragraphs, concrete and specific to this store, no real brands and no hype.")
        out = teacher.chat_json(sysmsg, prompt, _Article, temperature=0.8)
        body = str(out.get("body", "")).strip() if isinstance(out, dict) else ""
        if len(body) >= 120:
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            docs.append({"id": f"{spec['slug']}-{slug}", "title": str(out.get("title") or title).strip(),
                         "body": body})
    return docs


def _slug(vertical: str, name: str, i: int) -> str:
    # ASCII-fold first so accented (e.g. Hungarian) names slug cleanly instead of fragmenting.
    folded = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")[:32]
    return f"{vertical}-{base}-{i}"


def _price(val) -> float | None:
    if isinstance(val, (int, float)) and val > 0:
        return round(float(val), 2)
    m = re.search(r"\d+(?:\.\d+)?", str(val or ""))
    return round(float(m.group()), 2) if m else None


def synth_pack(spec: dict, teacher: Teacher, n: int = 30, batch: int = 12,
               loc: Locale | None = None) -> dict:
    """spec: {slug, store_name, vertical, brief, categories[], price_hint}. Returns a clean pack.

    Language is polymorphic via `loc` (a Locale): its synth_* methods supply the output-language
    directive and currency-sized prices — no per-language branching here. The English locale's
    defaults are neutral (no directive, identity price), so English synthesis is unchanged."""
    loc = loc or get_locale("en")
    sys = SYNTH_SYS + loc.synth_sys_suffix()
    lang_line = loc.synth_prompt_line()
    items: list[dict] = []
    seen: set[str] = set()
    for _ in range(n // batch + 4):
        if len(items) >= n:
            break
        avoid = ", ".join(list(seen)[-20:])
        prompt = (
            f"Store: {spec['store_name']} — {spec['brief']}\n"
            f"Categories: {', '.join(spec['categories'])}\n"
            f"Typical prices: {spec.get('price_hint', 'realistic for the vertical')}.{lang_line}\n"
            f"Invent {batch} DISTINCT catalog items spread across the categories. Each: an original "
            f"name, its category (use one of the category names above verbatim), a numeric price, a "
            f"one-line blurb, and a 2-3 sentence description consistent with the name/category/price."
            + (f" Do NOT repeat: {avoid}." if avoid else ""))
        for it in _items(teacher.chat_json(sys, prompt, CATALOG_SCHEMA, temperature=1.0)):
            name = str(it["name"]).strip()
            if name.lower() in seen or len(str(it["description"]).strip()) < 20:
                continue
            seen.add(name.lower())
            items.append(it)

    entities: list[dict] = []
    docs: list[dict] = _synth_docs(spec, teacher, loc)  # guide/policy articles first, then per-item
    for i, it in enumerate(items[:n]):
        name = str(it["name"]).strip()
        eid = _slug(spec["slug"], name, i)
        desc = str(it["description"]).strip()
        blurb = str(it.get("blurb") or "").strip() or desc[:120]
        base = _price(it.get("price"))
        entities.append({"id": eid, "title": name,
                         "group": str(it.get("category") or spec["slug"]).strip(),
                         "price": loc.synth_price(base) if base is not None else None,
                         "attrs": {}, "summary": blurb})
        docs.append({"id": f"{eid}-doc", "title": name, "body": desc})
    return {"slug": spec["slug"], "lang": loc.lang, "vertical": spec.get("vertical", spec["slug"]),
            "store_name": spec["store_name"], "entities": entities, "docs": docs}
