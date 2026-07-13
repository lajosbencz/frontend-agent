"""Reframe raw fact-seed packs into clean training packs via the teacher.

Reads data/seeds/*.json (from sample_amazon.py), rewrites each item's messy text into clean
grounded copy, writes data/packs/*.json (the canonical training input). Idempotent per pack; safe to
re-run. Use --only / --limit-items for quick quality checks before the full pass.

Usage: uv run python scripts/build_packs.py [--only electronics,books] [--limit-items 3]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kbft.adapters.pack import load_pack
from kbft.reframe import reframe_pack
from kbft.teacher import Teacher

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "data" / "seeds"
OUT_DIR = REPO / "data" / "packs"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated slugs")
    ap.add_argument("--limit-items", type=int, default=0, help="reframe only first N items/pack (test)")
    ap.add_argument("--model", default="qwen3.5:4b-q4_K_M")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--raw", default=str(RAW_DIR))
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    teacher = Teacher(model=args.model, workers=args.workers)

    raw_files = sorted(Path(args.raw).glob("*.json"))
    done = 0
    for f in raw_files:
        pack = load_pack(f)
        if only and pack["slug"] not in only:
            continue
        if args.limit_items:
            pack["entities"] = pack["entities"][: args.limit_items]
        print(f"[{pack['slug']}] reframing {len(pack['entities'])} items …")
        clean = reframe_pack(pack, teacher)
        (out / f"{pack['slug']}.json").write_text(json.dumps(clean, ensure_ascii=False, indent=1))
        print(f"[{pack['slug']}] wrote {len(clean['entities'])} clean items")
        done += 1
    print(f"\nReframed {done} packs -> {out}")


if __name__ == "__main__":
    main()
