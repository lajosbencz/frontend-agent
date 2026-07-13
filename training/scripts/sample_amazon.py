"""Sample per-category product metadata from Amazon-Reviews-2023 into domain packs.

The dataset uses a custom Python loader (the HF viewer refuses it), and modern `datasets`
dropped script execution — so we stream the raw per-category metadata files directly and read
only the first valid items, aborting the download early. The per-category files are plain
(uncompressed) JSONL, so reading the first N lines fetches only a few MB even of the 14GB Books
file. No loader script, no full download.

Each category -> one pack JSON: {slug, vertical, store_name, entities[], docs[]}, where entities
are catalog items (id/title/group/price/attrs) and docs are per-product KB passages (features +
description) used as search_knowledge grounding. Personas/tools/negatives are added later by the
generic pack loader; this script only produces the catalog + KB text.

Usage: uv run python scripts/sample_amazon.py [--n 45] [--only electronics,books]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACK_DIR = REPO / "data" / "seeds"  # raw fact-seed packs; built into data/packs/ by build_packs
BASE = ("https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/"
        "raw/meta_categories/meta_{cat}.jsonl")

# vertical slug -> (Amazon category file stem, synthetic store name). ~18 diverse verticals; store
# names are cosmetic (persona flavor), the catalog/KB come from the data.
CATEGORIES: dict[str, tuple[str, str]] = {
    "electronics":  ("Electronics", "VoltEdge"),
    "fashion":      ("Amazon_Fashion", "Thread&Co"),
    "home":         ("Home_and_Kitchen", "Hearth & Hollow"),
    "beauty":       ("Beauty_and_Personal_Care", "Lumière"),
    "books":        ("Books", "Margin Notes"),
    "sports":       ("Sports_and_Outdoors", "Summit Line"),
    "toys":         ("Toys_and_Games", "Playful"),
    "grocery":      ("Grocery_and_Gourmet_Food", "The Pantry"),
    "hardware":     ("Tools_and_Home_Improvement", "BoltHouse"),
    "pet":          ("Pet_Supplies", "Paws & Co"),
    "auto":         ("Automotive", "DriveLine"),
    "office":       ("Office_Products", "Deskwork"),
    "garden":       ("Patio_Lawn_and_Garden", "Greenside"),
    "instruments":  ("Musical_Instruments", "Chord & Key"),
    "phones":       ("Cell_Phones_and_Accessories", "Signal"),
    "health":       ("Health_and_Household", "Wellspring"),
    "videogames":   ("Video_Games", "Respawn"),
    "crafts":       ("Arts_Crafts_and_Sewing", "Makers Row"),
}

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_PRICE = re.compile(r"\d+(?:\.\d+)?")


def clean(text: str, cap: int = 600) -> str:
    text = _WS.sub(" ", _TAG.sub(" ", text or "")).strip()
    return text[:cap].rstrip()


def join_text(val) -> str:
    """features/description come as list[str] (sometimes str); join to one blob."""
    if isinstance(val, list):
        return " ".join(str(x) for x in val if x)
    return str(val or "")


def parse_price(val) -> float | None:
    if isinstance(val, (int, float)):
        return float(val) if val and val > 0 else None
    m = _PRICE.search(str(val or ""))
    if not m:
        return None
    try:
        p = float(m.group())
        return p if p > 0 else None
    except ValueError:
        return None


def subgroup(categories, fallback: str) -> str:
    """A realistic sub-group label from the item's category path (e.g. 'Headphones')."""
    if isinstance(categories, list) and len(categories) > 1 and categories[1]:
        return clean(str(categories[1]), cap=40) or fallback
    return fallback


def sample_category(slug: str, cat: str, store: str, n: int, scan_cap: int) -> dict | None:
    url = BASE.format(cat=cat)
    print(f"[{slug}] streaming {cat} …")
    entities: list[dict] = []
    docs: list[dict] = []
    seen_titles: set[str] = set()
    scanned = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kbft-sampler/1.0"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            for raw in resp:  # plain JSONL; iterating the response streams + aborts early on break
                if scanned >= scan_cap or len(entities) >= n:
                    break
                scanned += 1
                try:
                    r = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue
                title = clean(str(r.get("title") or ""), cap=120)
                text = clean(join_text(r.get("features")) + " " + join_text(r.get("description")))
                asin = r.get("parent_asin") or r.get("asin")
                if not title or not asin or len(text) < 30:
                    continue
                key = title.lower()
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                eid = f"{slug}-{asin}"
                attrs = {}
                store_brand = r.get("store")
                if store_brand:
                    attrs["brand"] = clean(str(store_brand), cap=40)
                rating = r.get("average_rating")
                if isinstance(rating, (int, float)) and rating:
                    attrs["rating"] = round(float(rating), 1)
                entities.append({
                    "id": eid,
                    "title": title,
                    "group": subgroup(r.get("categories"), slug),
                    "price": parse_price(r.get("price")),
                    "attrs": attrs,
                })
                docs.append({"id": f"{eid}-doc", "title": title, "body": text})
    except Exception as e:  # noqa: BLE001 — skip a category that fails to fetch
        print(f"[{slug}] FAILED: {type(e).__name__}: {str(e)[:120]}")
        return None
    if not entities:
        print(f"[{slug}] no valid items (scanned {scanned})")
        return None
    print(f"[{slug}] kept {len(entities)} items (scanned {scanned})")
    return {"slug": slug, "vertical": slug, "store_name": store,
            "entities": entities, "docs": docs}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=45, help="valid items per category")
    ap.add_argument("--scan-cap-mult", type=int, default=25,
                    help="max rows scanned per category = n * this (bounds early-abort download)")
    ap.add_argument("--only", default="", help="comma-separated slugs to limit to")
    ap.add_argument("--out", default=str(PACK_DIR))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    targets = {k: v for k, v in CATEGORIES.items() if not only or k in only}

    written, total_items = 0, 0
    for slug, (cat, store) in targets.items():
        pack = sample_category(slug, cat, store, args.n, args.n * args.scan_cap_mult)
        if not pack:
            continue
        (out / f"{slug}.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1))
        written += 1
        total_items += len(pack["entities"])
    print(f"\nWrote {written}/{len(targets)} packs, {total_items} catalog items -> {out}")


if __name__ == "__main__":
    main()
