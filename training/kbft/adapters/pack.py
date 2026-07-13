"""Pack ingestion adapter: a domain pack (dict/JSON) -> normalized KB IR.

A pack is the portable, source-agnostic unit produced by sample_amazon.py (real catalogs) or the
teacher synthesizer (exotic verticals): {slug, vertical, store_name, entities[], docs[]}. This
adapter maps it onto the same KB(docs, entities) IR the markdown adapter produces, so every
downstream stage (context, recipes, render) is identical whether a domain came from markdown or a
pack. Two normalizations happen here:

- Synthetic price fallback: real Amazon meta omits price ~40% of the time; price-dependent recipes
  (search under $X, comparisons) need one. Missing prices are filled deterministically from the id,
  inside the pack's own real price band, so they match the vertical's scale and are stable per item.
- Entity summaries: pulled from the matching product doc body (first sentence), giving catalog
  context + search something concise to show without the full KB passage.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from kbft.schema import KB, Doc, Entity

_SENT = re.compile(r"(.+?[.!?])(?:\s|$)")


def _first_sentence(text: str, cap: int = 160) -> str:
    m = _SENT.match(text.strip())
    s = m.group(1) if m else text.strip()
    return s[:cap].rstrip()


def _doc_prose(body: str, cap: int = 320) -> str:
    """Clean grounded prose for a doc: the description text BEFORE the attribute-bullet block.

    Pack bodies are built as `<prose sentences>\\n- attr\\n- attr…`; the prose is the human-written
    summary, the bullets are structured attrs (often bare labels like `- brand`). Normalizing this
    ONCE here — at the adapter boundary where raw data becomes the domain model — means recipes read
    a clean field and never parse bodies themselves. Whole sentences only, capped."""
    text = (body or "").strip()
    cut = re.split(r"\n\s*[-•*]", text, maxsplit=1)[0].strip()  # drop the bullet block
    cut = re.sub(r"\s+", " ", cut)
    if not cut:  # bullet-first body (no leading prose): fall back to the first sentence of the whole
        return _first_sentence(text, cap)
    if len(cut) <= cap:
        return cut
    m = max(cut.rfind(". ", 0, cap), cut.rfind("! ", 0, cap), cut.rfind("? ", 0, cap))
    return cut[:m + 1] if m > 40 else _first_sentence(cut, cap)


def _synth_price(eid: str, lo: float, hi: float) -> float:
    """Deterministic plausible price in [lo, hi] from the id (stable per item)."""
    h = int(hashlib.md5(eid.encode()).hexdigest()[:8], 16)
    val = lo + (h % 1000) / 1000.0 * max(1.0, hi - lo)
    return round(val, 2)


def _synth_stock(eid: str, oos_frac: float = 0.15) -> bool:
    """Deterministic availability so ~oos_frac of items are out of stock — drives availability-aware
    recipes (decline to add an OOS item). Stable per item."""
    h = int(hashlib.md5((eid + "|stock").encode()).hexdigest()[:8], 16)
    return (h % 1000) / 1000.0 >= oos_frac


_SLUG = re.compile(r"[^a-z0-9]+")


def _ascii_fold(s: str) -> str:
    """Strip diacritics so accented titles slug cleanly (Hungarian 'Jármű' -> 'jarmu') instead of
    dropping the accented letters and fragmenting the word. No-op for pure-ASCII English."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _slug_id(title: str, fallback: str) -> str:
    s = _SLUG.sub("-", _ascii_fold(title or "").lower()).strip("-")[:32].rstrip("-")
    return s or fallback


class PackAdapter:
    def __init__(self, pack: dict, semantic_ids: bool = False) -> None:
        self.pack = pack
        # semantic_ids: rewrite opaque ids (Amazon ASINs) to hyphenated title-slugs like the demo's
        # `flux-machine`. Training on BOTH id styles teaches the model that an id is an opaque atom to
        # copy VERBATIM from results — it must not truncate `flux-machine` to the query word `flux`.
        self.semantic_ids = semantic_ids

    def ingest(self) -> KB:
        pack = self.pack
        doc_body = {d["id"]: d.get("body", "") for d in pack.get("docs", [])}

        real = [e["price"] for e in pack["entities"] if e.get("price")]
        lo, hi = (min(real), max(real)) if real else (7.0, 149.0)

        # id remap (opaque -> title-slug), collision-safe; keeps _synth_* stable via the ORIGINAL id
        id_map: dict[str, str] = {}
        if self.semantic_ids:
            used: set[str] = set()
            for e in pack["entities"]:
                base = _slug_id(e.get("title", ""), e["id"])
                nid, k = base, 2
                while nid in used:
                    nid, k = f"{base}-{k}", k + 1
                used.add(nid)
                id_map[e["id"]] = nid

        entities: list[Entity] = []
        for e in pack["entities"]:
            oid = e["id"]
            price = e.get("price")
            if price is None:
                price = _synth_price(oid, lo, hi)
            body = doc_body.get(f"{oid}-doc", "")
            entities.append(Entity(
                id=id_map.get(oid, oid),
                title=e["title"],
                group=e.get("group") or pack["slug"],
                # clean packs carry a teacher-written blurb; raw packs fall back to first sentence
                summary=e.get("summary") or _first_sentence(body),
                body=body,
                price=float(price),
                in_stock=_synth_stock(oid),
                attrs=e.get("attrs", {}),
            ))

        docs: list[Doc] = []
        for d in pack.get("docs", []):
            did = d["id"]
            # keep entity-doc links pointing at the (possibly remapped) entity id
            if did.endswith("-doc") and did[:-4] in id_map:
                did = f"{id_map[did[:-4]]}-doc"
            docs.append(Doc(
                id=did,
                title=d.get("title", ""),
                description=_doc_prose(d.get("body", "")),
                body=d.get("body", ""),
            ))
        return KB(docs=docs, entities=entities)


def load_pack(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def load_all_packs(pack_dir: str | Path) -> list[dict]:
    """All packs in a directory, sorted by slug for deterministic ordering."""
    return [load_pack(p) for p in sorted(Path(pack_dir).glob("*.json"))]
