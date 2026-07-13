"""Single source of truth for the EVAL held-out domains.

These domains are the evaluation set: they must NEVER appear in training data, or every held-out
score is invalidated. Generation excludes them FAIL-CLOSED (not via an optional CLI flag), snapshot
VERIFIES their absence in the emitted train file, and eval uses exactly these. Change the eval domain
in ONE place here — no per-script defaults to drift out of sync (that drift was the leakage moat)."""
from __future__ import annotations

import json
from pathlib import Path

# Domains held out for evaluation. `videogames` is a data/packs/*.json pack (the real leak risk, since
# generation iterates packs); `brewcraft` is an eval/ fixture (never a training pack) but is listed
# here so the invariant is complete and self-documenting.
EVAL_HOLDOUT = frozenset({"videogames", "brewcraft",
                          # generalist-breadth eval domains (unseen verticals), added for a fair
                          # generalist average rather than scoring on two example domains.
                          "pharmacy", "carrental", "restaurant", "florist"})


def eval_pack_ids(pack_dir: str | Path) -> set[str]:
    """Entity + doc ids of the held-out PACKS (used to grep the train file for leakage). Domain-module
    holdouts (brewcraft) have no pack file and are structurally absent from pack-based training."""
    ids: set[str] = set()
    for slug in EVAL_HOLDOUT:
        pth = Path(pack_dir) / f"{slug}.json"
        if not pth.exists():
            continue
        data = json.loads(pth.read_text())
        for item in data.get("entities", []) + data.get("catalog", []) + data.get("docs", []):
            if isinstance(item, dict) and item.get("id"):
                ids.add(str(item["id"]))
    return ids


def assert_no_leakage(train_jsonl: str | Path, pack_dir: str | Path) -> int:
    """Hard-fail if any held-out entity/doc id appears in the train file. Returns the count checked.
    Call this after generation and again in snapshot — trust verification, not a CLI flag."""
    ids = eval_pack_ids(pack_dir)
    if not ids:
        return 0
    text = Path(train_jsonl).read_text()
    # ids are distinctive (e.g. "videogames-B07..."); a plain substring scan is sufficient and cheap.
    hits = sorted({i for i in ids if i in text})
    if hits:
        raise SystemExit(f"HELD-OUT LEAKAGE: {len(hits)} eval-domain id(s) found in {train_jsonl} "
                         f"(e.g. {hits[:5]}). Aborting — the eval set is contaminated.")
    return len(ids)
