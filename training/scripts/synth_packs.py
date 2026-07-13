"""Generate teacher-synthesized exotic packs into data/packs/ (clean; no reframe needed).

Language is generic: `--lang <l>` makes the teacher author the catalog + KB in that language (via the
locale's directive) and sizes prices for its currency; the pack is written as `<slug>-<l>.json` with
`lang: <l>` so it never collides with the English twin and is picked up per-language downstream. Same
verticals, different language — NOT a bespoke per-language domain.

Usage: uv run python scripts/synth_packs.py [--only crypto,movies] [--n 30] [--lang hu --provider openrouter]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kbft.locales import get_locale
from kbft.synth import synth_pack
from kbft.teacher import Teacher

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "packs"

# Verticals HF lacks — fictional stores the teacher invents. Kept generic; "cart" semantics apply
# loosely (buy/hold/book) which is fine — the point is topic-agnostic interaction patterns.
SPECS: dict[str, dict] = {
    "crypto": {"slug": "crypto", "store_name": "CoinBazaar", "vertical": "crypto token marketplace",
               "brief": "a marketplace listing crypto tokens and coins to buy",
               "categories": ["Layer 1", "DeFi", "Stablecoin", "Meme", "Gaming", "Privacy"],
               "price_hint": "$0.01 to $60000 (wide range)"},
    "movies": {"slug": "movies", "store_name": "ReelVault", "vertical": "movie collectible store",
               "brief": "a store selling collectible film editions (original, invented titles)",
               "categories": ["Sci-Fi", "Drama", "Comedy", "Horror", "Documentary", "Animation"],
               "price_hint": "$9.99 to $49.99"},
    "tshirts": {"slug": "tshirts", "store_name": "InkThread", "vertical": "custom t-shirt store",
                "brief": "a store selling original graphic t-shirt designs",
                "categories": ["Graphic", "Vintage", "Minimalist", "Typography", "Nature", "Retro"],
                "price_hint": "$14.99 to $39.99"},
    "portfolio": {"slug": "portfolio", "store_name": "Studio Nine", "vertical": "design services studio",
                  "brief": "a design studio offering bookable creative service packages",
                  "categories": ["Branding", "Web Design", "Illustration", "Motion", "Copywriting"],
                  "price_hint": "$250 to $8000"},
    "saas": {"slug": "saas", "store_name": "StackYard", "vertical": "software marketplace",
             "brief": "a marketplace of invented SaaS apps and subscription plans",
             "categories": ["Productivity", "Analytics", "Security", "DevTools", "Marketing"],
             "price_hint": "$5 to $499 per month"},
    "tickets": {"slug": "tickets", "store_name": "PassGate", "vertical": "event ticketing site",
                "brief": "an event ticketing site for invented concerts, expos, and shows",
                "categories": ["Concert", "Theater", "Sports", "Conference", "Festival"],
                "price_hint": "$19 to $450"},
    # --- doubled set (avoid held-out demo domains: espresso/coffee gear + video games) ---
    "plants": {"slug": "plants", "store_name": "Verdant", "vertical": "indoor plant shop",
               "brief": "a shop selling houseplants, planters, and plant-care supplies",
               "categories": ["Foliage", "Succulent", "Flowering", "Planters", "Care"],
               "price_hint": "$6 to $180"},
    "sneakers": {"slug": "sneakers", "store_name": "Sole Theory", "vertical": "sneaker store",
                 "brief": "a store selling original-design sneakers and footwear",
                 "categories": ["Running", "Lifestyle", "Skate", "Trail", "Court"],
                 "price_hint": "$45 to $220"},
    "vinyl": {"slug": "vinyl", "store_name": "Groove Theory", "vertical": "vinyl record shop",
              "brief": "a shop selling collectible vinyl records by invented artists",
              "categories": ["Jazz", "Rock", "Electronic", "Soul", "Ambient", "Folk"],
              "price_hint": "$18 to $80"},
    "stationery": {"slug": "stationery", "store_name": "Inkwell & Co", "vertical": "stationery store",
                   "brief": "a store selling pens, notebooks, and desk goods",
                   "categories": ["Pens", "Notebooks", "Desk", "Paper", "Gifts"],
                   "price_hint": "$3 to $90"},
    "skincare": {"slug": "skincare", "store_name": "Lumen", "vertical": "skincare shop",
                 "brief": "a shop selling original-brand skincare and grooming products",
                 "categories": ["Cleanser", "Serum", "Moisturizer", "Sun", "Masks"],
                 "price_hint": "$9 to $120"},
    "camping": {"slug": "camping", "store_name": "TrailHead", "vertical": "outdoor gear store",
                "brief": "a store selling camping and hiking gear",
                "categories": ["Tents", "Sleep", "Cook", "Packs", "Apparel"],
                "price_hint": "$12 to $600"},
    # --- held-out-only eval verticals (unseen in training): generalist-breadth domains ---
    "pharmacy": {"slug": "pharmacy", "store_name": "WellNest Pharmacy", "vertical": "pharmacy & wellness store",
                 "brief": "a pharmacy selling OTC medicine, vitamins, and personal-care goods",
                 "categories": ["OTC", "Vitamins", "First Aid", "Personal Care", "Baby"],
                 "price_hint": "$3 to $80"},
    "carrental": {"slug": "carrental", "store_name": "DriveAway", "vertical": "car rental service",
                  "brief": "a service to book rental cars by class (buy/book semantics apply loosely)",
                  "categories": ["Economy", "SUV", "Luxury", "Van", "Electric"],
                  "price_hint": "$29 to $350 per day"},
    "restaurant": {"slug": "restaurant", "store_name": "Fork & Flame", "vertical": "restaurant menu",
                   "brief": "a restaurant menu for ordering dishes (invented dishes)",
                   "categories": ["Starters", "Mains", "Desserts", "Drinks", "Sides"],
                   "price_hint": "$4 to $38"},
    "florist": {"slug": "florist", "store_name": "Bloom & Stem", "vertical": "florist shop",
                "brief": "a florist selling bouquets, arrangements, and gifting add-ons",
                "categories": ["Bouquets", "Arrangements", "Plants", "Occasions", "Add-ons"],
                "price_hint": "$15 to $150"},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated vertical slugs")
    ap.add_argument("--n", type=int, default=30, help="items per pack")
    ap.add_argument("--provider", default="ollama", choices=["ollama", "openrouter"])
    ap.add_argument("--model", default="qwen3.5:4b-q4_K_M")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--lang", default="en", help="author the catalog + KB in this language (generic)")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    loc = get_locale(args.lang)
    teacher = Teacher(provider=args.provider, model=args.model, workers=args.workers)

    for slug, spec in SPECS.items():
        if only and slug not in only:
            continue
        # locale's pack_suffix tags non-en files so a hu pack coexists with its en twin
        # (crypto.json / crypto-hu.json); en's suffix is "" — no branch needed.
        pslug = f"{slug}{loc.pack_suffix}"
        print(f"[{pslug}] synthesizing {args.n} items (lang={args.lang}) …")
        pack = synth_pack({**spec, "slug": pslug}, teacher, n=args.n, loc=loc)
        (out / f"{pslug}.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1))
        print(f"[{pslug}] wrote {len(pack['entities'])} items")


if __name__ == "__main__":
    main()
