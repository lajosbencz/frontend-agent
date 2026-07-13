"""Print a representative, human-readable sample of the generated training data.

Runs each generic recipe on a few diverse packs and pretty-prints decoded conversations labeled by
recipe + pack, so we can eyeball grounding, refusals, tool calls, and alias consistency before a full
run. Not part of the pipeline — a QA lens.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kbft.adapters.pack import PackAdapter, load_pack
from kbft.generic_gen import (GenConfig, GenCounts, PackCtx, catalog_add, catalog_browse,
                              rag_answer, rag_refuse, ref_add)
from kbft.teacher import Teacher

REPO = Path(__file__).resolve().parents[1]
PACKS = ["electronics", "fashion", "hardware", "beauty"]
RECIPES = [("rag_answer", rag_answer), ("rag_refuse", rag_refuse),
           ("catalog_add", catalog_add), ("catalog_browse", catalog_browse), ("ref_add", ref_add)]


def show(ex, tools) -> None:
    names = [t["function"]["name"] for t in tools]
    print(f"  tools: {', '.join(names)}")
    print(f"  [system] {ex.system.splitlines()[0][:110]}…")
    for t in ex.turns:
        role = t["role"]
        if role == "user":
            print(f"  [user] {t['content']}")
        elif role == "tool":
            payload = json.loads(t["content"])
            if "results" in payload:
                rs = payload["results"]
                inner = " | ".join(f"{r['title'][:40]} (score {r.get('score','?')})" for r in rs[:3])
                print(f"  [tool] {len(rs)} results: {inner or '(none)'}")
            else:
                print(f"  [tool] {t['content'][:90]}")
        elif t.get("tool_calls"):
            for c in t["tool_calls"]:
                f = c["function"]
                print(f"  [assistant→call] {f['name']}({json.dumps(f['arguments'])})")
        else:
            print(f"  [assistant] {t['content']}")


def main() -> None:
    cfg = GenConfig(teacher=Teacher(model="qwen3.5:4b-q4_K_M", workers=8),
                    counts=GenCounts(rag_answer=2, rag_refuse=2, catalog_add=2,
                                     catalog_browse=2, ref_add=2))
    rng = random.Random(7)
    # one recipe per pack, rotating, so we see both recipe and vertical diversity
    for i, (name, recipe) in enumerate(RECIPES):
        pack_slug = PACKS[i % len(PACKS)]
        pack = load_pack(REPO / "data" / "packs" / f"{pack_slug}.json")
        ctx = PackCtx(pack, PackAdapter(pack).ingest(), cfg, rng)
        exs = recipe(ctx)
        print(f"\n{'=' * 78}\n### {name.upper()}  —  pack: {pack_slug}\n{'=' * 78}")
        if not exs:
            print("  (no examples produced)")
            continue
        show(exs[0], ctx.tools)


if __name__ == "__main__":
    main()
