"""Deterministic multi-turn-rich release datasets for the 350M capacity experiment.

Same distribution as dataset_40m (all-flash flbig base + all-flash grounded-refusal), built at two
scales that are NESTED (20M subset of 40M) via one shuffle + seed, so 20M-vs-40M isolates volume.
Reproducible: fixed SEED. Run: PYTHONPATH=. .venv/bin/python scripts/build_release_multiturn.py
"""
from __future__ import annotations

import random
from pathlib import Path

from kbft.render import finalize_from_raw

REPO = Path(__file__).resolve().parents[1]
BASE_RAW = REPO / "data/dataset_flbig/raw_generated.jsonl"          # all-flash multi-turn-rich (sessions6 scale7)
REFUSE_RAW = REPO / "data/_refuse_topup_flash/raw_generated.jsonl"  # all-flash refusal, seed 660066
SEED = 404040  # identical to build_release_40m: shuffle base only, append refuse in order

# 20M = nested subset of the existing data/dataset_40m (base[:14000] + refuse[:1137]).
OUT, BASE_KEEP, REFUSE_KEEP = "data/dataset_mt20m", 14000, 1137


def main() -> None:
    base = list(open(BASE_RAW))
    refuse = list(open(REFUSE_RAW))            # NOT shuffled — matches build_release_40m
    random.Random(SEED).shuffle(base)
    d = REPO / OUT
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "raw_generated.jsonl", "w") as w:
        w.writelines(base[:BASE_KEEP])
        w.writelines(refuse[:REFUSE_KEEP])
    stats = finalize_from_raw(d)
    print(f"{OUT}: base {BASE_KEEP} + refuse {REFUSE_KEEP} -> {stats}")


if __name__ == "__main__":
    main()
