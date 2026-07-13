"""Deterministic ~40M-token dataset build: all-flash base (flbig) + all-flash grounded-refusal top-up.

Scales the winning lean+refuse recipe to ~40M dataset tokens to test whether volume improves quality.
Reproducible: fixed SEED for the base subsample; source raws + seed recorded here. Run:
  PYTHONPATH=. .venv/bin/python scripts/build_release_40m.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from kbft.render import finalize_from_raw

REPO = Path(__file__).resolve().parents[1]
BASE_RAW = REPO / "data/dataset_flbig/raw_generated.jsonl"        # all-flash scale7, 48.7M tok
REFUSE_RAW = REPO / "data/_refuse_topup_flash/raw_generated.jsonl"  # all-flash refusal, seed 660066
OUT = REPO / "data/dataset_40m"
SEED = 404040
BASE_KEEP = 28000  # subsample flbig so base+refusal lands ~40M dataset tokens


def main() -> None:
    base = [l for l in open(BASE_RAW)]
    refuse = [l for l in open(REFUSE_RAW)]
    rng = random.Random(SEED)
    rng.shuffle(base)
    kept = base[:BASE_KEEP]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "raw_generated.jsonl", "w") as w:
        w.writelines(kept)
        w.writelines(refuse)
    print(f"base {len(base)} -> kept {len(kept)} + refuse {len(refuse)} = {len(kept)+len(refuse)} raw")
    stats = finalize_from_raw(OUT)
    print("STATS", stats)


if __name__ == "__main__":
    main()
