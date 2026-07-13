"""Extract the publishable, synthetic-only subset of a dataset version.

The full training set mixes fully-synthetic packs with real-catalog packs reframed from
Amazon-Reviews-2023 (real brands/ASINs). Only the synthetic packs are redistributable, so this
filters the rendered rows down to those grounded in a synthetic store, guarding that no real-catalog
store, entity id, or brand leaks through. Credit-free: pure filtering of existing rows, no teacher.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kbft.adapters.pack import PackAdapter, load_all_packs
from kbft.holdout import EVAL_HOLDOUT

REPO = Path(__file__).resolve().parents[1]

SYNTH = {"crypto", "movies", "portfolio", "saas", "tickets", "tshirts"}


def _sem(slug: str) -> bool:
    return int(hashlib.md5(slug.encode()).hexdigest(), 16) % 2 == 0


def _pack_markers(pack: dict) -> tuple[str, set[str], set[str]]:
    """(store_name, entity+doc ids, real brands) exactly as they render in the SFT rows."""
    kb = PackAdapter(pack, semantic_ids=_sem(pack["slug"])).ingest()
    ids = {e.id for e in kb.entities} | {d.id for d in kb.docs}
    brands = {str(e.attrs.get("brand", "")).strip() for e in kb.entities}
    brands = {b for b in brands if len(b) >= 3}
    return pack.get("store_name", ""), ids, brands


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", default=str(REPO / "data" / "dataset"),
                    help="dataset dir with sft_*.jsonl (the working data/dataset/, or a snapshot from "
                         "snapshot_dataset.py)")
    ap.add_argument("--version", default="v1.0.0", help="label for the dataset card")
    ap.add_argument("--packs", default=str(REPO / "data" / "packs"))
    ap.add_argument("--out", default=str(REPO / "artifacts" / "gguf" / "publish" / "hf-dataset"))
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    packs = {p["slug"]: p for p in load_all_packs(args.packs)
             if p.get("lang", "en") == "en" and p["slug"] not in EVAL_HOLDOUT}

    synth_stores, amazon_stores, amazon_ids, amazon_brands = set(), set(), set(), set()
    for slug, pack in packs.items():
        store, ids, brands = _pack_markers(pack)
        if slug in SYNTH:
            synth_stores.add(store)
        else:
            amazon_stores.add(store)
            amazon_ids |= ids
            amazon_brands |= brands
    amazon_stores.discard("")
    print(f"synth stores ({len(synth_stores)}): {sorted(synth_stores)}")
    print(f"amazon markers: {len(amazon_stores)} stores, {len(amazon_ids)} ids, {len(amazon_brands)} brands")

    def keep(text: str) -> bool:
        if not any(s in text for s in synth_stores):
            return False
        if any(s in text for s in amazon_stores):
            return False
        return True

    manifest = {"version": args.version, "subset": "synthetic-only", "source_version": args.version,
                "synthetic_packs": sorted(SYNTH), "files": {}}
    leak = 0
    for split in ("sft_train.jsonl", "sft_eval.jsonl"):
        rows_in = (src / split).read_text().splitlines()
        kept = []
        for line in rows_in:
            if not line.strip():
                continue
            text = json.loads(line)["text"]
            if keep(text):
                # hard guard: reject if any real-catalog id/brand slipped in
                if any(aid in text for aid in amazon_ids) or any(b in text for b in amazon_brands):
                    leak += 1
                    continue
                kept.append(line)
        (out / split).write_text("\n".join(kept) + "\n")
        sha = hashlib.sha256("\n".join(kept).encode()).hexdigest()[:12]
        manifest["files"][split] = {"lines": len(kept), "sha256_12": sha}
        print(f"{split}: {len(rows_in)} -> {len(kept)} rows kept")
    if leak:
        print(f"[guard] dropped {leak} rows that matched a synth store but carried a real-catalog id/brand")

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (out / "README.md").write_text(_card(args.version, manifest))
    print(f"[done] wrote subset + card to {out}")


def _card(version: str, m: dict) -> str:
    tr = m["files"]["sft_train.jsonl"]["lines"]
    ev = m["files"]["sft_eval.jsonl"]["lines"]
    return f"""---
license: cc-by-4.0
task_categories:
- text-generation
tags:
- tool-use
- function-calling
- rag
- agent
- synthetic
language:
- en
pretty_name: frontend-agent SFT (synthetic subset)
---

# frontend-agent SFT — synthetic subset ({version})

Supervised fine-tuning data for a generic, retriever-agnostic **web/front-end agent** (tool calling
+ RAG-grounded answering) on `LiquidAI/LFM2.5-230M`. This is the **fully-synthetic subset** of the
{version} training generation: every row is grounded in an invented store/catalog, so it carries no
third-party catalog data. Trains behaviors, not facts — grounding is supplied at runtime.

- `sft_train.jsonl` — {tr} rows · `sft_eval.jsonl` — {ev} rows
- Format: JSONL, one object per line: `{{"text": <chat-template-rendered conversation>}}`
- Synthetic verticals: {", ".join(m["synthetic_packs"])}

## How it was made

Compositional generation: tool calls, ids, and tool results are assembled deterministically; a
teacher LLM (`google/gemini-2.5-flash`) writes only the natural-language surface (user messages,
grounded replies), constrained to the retrieved results. Tool and argument names are randomized per
example so the model must read the injected schema. See the project repo for method and code.

## Provenance & licensing

Synthetic catalogs and knowledge base are LLM-invented (original names; no real brands). The
natural-language surface is **LLM-assisted** (`google/gemini-2.5-flash` via OpenRouter). Released
under **CC-BY-4.0** — free to use, including commercially, with attribution. The real-catalog packs
used elsewhere in training (reframed from Amazon-Reviews-2023) are **not** included here.

Aligned model: `lfm2.5-230m-frontend-agent` ({version}).
"""


if __name__ == "__main__":
    main()
