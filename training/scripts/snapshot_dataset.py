"""Archive a completed generation run into a labeled, HF-ready dataset snapshot.

Generation overwrites data/dataset/ in place; this freezes a run into `--out/<version>/` (an immutable
copy of the split + raw dump + packs used, plus provenance/stats and a HuggingFace dataset card). It's
optional — versioning lives in git tags + the published HF dataset, and nothing here is committed.
`--out` defaults to data/releases/ (gitignored); point it anywhere to keep your own version archive.

Publishing to the Hub is a MANUAL, gated step — this script NEVER pushes.

Usage:
  uv run python scripts/snapshot_dataset.py --version v1.1.0 --held-out videogames --out data/releases
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kbft.holdout import EVAL_HOLDOUT, assert_no_leakage

REPO = Path(__file__).resolve().parents[1]
DATASET = REPO / "data" / "dataset"
PACK_DIR = REPO / "data" / "packs"
RELEASES = REPO / "data" / "releases"  # default snapshot dir (gitignored); override with --out

MODEL_ID = "LiquidAI/LFM2.5-230M"
TEACHER = "qwen3.5:4b-q4_K_M"


def sha12(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def count_lines(path: Path) -> int:
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def token_stats(path: Path, model_id: str) -> dict:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id)
    lens = [len(tok(json.loads(line)["text"], add_special_tokens=False)["input_ids"])
            for line in open(path)]
    lens.sort()
    n = len(lens)
    return {"examples": n, "total_tokens": sum(lens),
            "mean_tokens": round(sum(lens) / n, 1) if n else 0,
            "p50": lens[n // 2] if n else 0, "p95": lens[int(n * 0.95)] if n else 0,
            "max": lens[-1] if n else 0}


DATASET_CARD = """---
license: other
task_categories:
- text-generation
tags:
- tool-use
- function-calling
- rag
- e-commerce
- synthetic
language:
- {lang}
---

# Generic RAG e-commerce tool-use SFT — {version}

Synthetic supervised-fine-tuning data for a **retriever-agnostic, tool-calling shopping assistant**
(target model: `{model_id}`, 230M). Every grounded answer is written from **search-tool results
only** (RAG-as-a-tool), and tool/argument names are **procedurally randomized per example** so the
model learns to read the injected schema rather than memorize a fixed toolset.

## How it was generated

Compositional generation: deterministic tool calls, ids, and tool results are assembled by recipe
code across a set of domain *packs*; a teacher model (`{teacher}`) writes only the natural-language
surface (customer messages, grounded replies), constrained to the retrieved results. See
`docs/base-training-procedure.md` for the method (§7a ground-truth-from-retrieval, §7b genericity).

- **Frozen tool contract (result shape):** `search_catalog`, `search_knowledge`, `add_to_cart`,
  `remove_from_cart`, `view_cart`, `clear_cart`.
- **Held-out domain(s):** `{held_out}` — excluded from training for held-out evaluation.
- **Format:** JSONL, one object per line: `{{"text": <chat-template-rendered conversation>}}`.

## Files

| file | examples |
|---|---|
| `sft_train.jsonl` | {n_train} |
| `sft_eval.jsonl` | {n_eval} |
| `raw_generated.jsonl` | {n_raw} (pre-dedup/split dump) |
| `packs/` | domain packs used as input |

## Provenance

- scale (passes): {scale} · seed: {seed} · generated: {generated}
- teacher: `{teacher}` · tokenizer/template: `{model_id}`
- **aligned model:** this dataset trains `{model_gguf}-<QUANT>.gguf` (dataset & model share version `{version}`)
{note}

## License / attribution

Real-catalog packs are reframed from **Amazon-Reviews-2023** metadata; exotic verticals are fully
teacher-synthesized (fictional). Review source-data licensing before redistribution.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="version label, e.g. v1.1.0")
    ap.add_argument("--from", dest="src", default=str(DATASET))
    ap.add_argument("--out", default=str(RELEASES), help="snapshot root; writes <out>/<version>/ "
                    "(default data/releases/, gitignored — point anywhere for your own versioning)")
    ap.add_argument("--packs", default=str(PACK_DIR))
    ap.add_argument("--scale", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260707)
    ap.add_argument("--held-out", default="videogames")
    ap.add_argument("--lang", default="en", help="language of this run — only same-language packs are "
                    "archived (one model = one language, no mixing)")
    ap.add_argument("--teacher", default=TEACHER)
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--model-name", default="lfm2.5-230m",
                    help="GGUF base name; the trained model built from this dataset is "
                         "<model-name>-<version>-<QUANT>.gguf (dataset & model versions stay aligned)")
    ap.add_argument("--note", default="")
    ap.add_argument("--no-tokens", action="store_true", help="skip token stats (faster)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    dest = Path(args.out) / args.version
    if dest.exists() and not args.force:
        raise SystemExit(f"{dest} exists — pick a new --version or pass --force")
    dest.mkdir(parents=True, exist_ok=True)

    files = {}
    for name in ("sft_train.jsonl", "sft_eval.jsonl", "raw_generated.jsonl"):
        s = src / name
        if not s.exists():
            print(f"  WARN: {s} missing, skipping")
            continue
        shutil.copy2(s, dest / name)
        files[name] = {"lines": count_lines(dest / name), "sha256_12": sha12(dest / name),
                       "bytes": (dest / name).stat().st_size}

    # GATE: verify the copied train split carries no eval-domain ids (trust the data, not a flag).
    if (dest / "sft_train.jsonl").exists():
        checked = assert_no_leakage(dest / "sft_train.jsonl", args.packs)
        print(f"  leakage check OK: 0 of {checked} held-out ids in sft_train.jsonl")

    # Ingest the generator's run-manifest (real provenance) if present; fall back to CLI otherwise.
    run_mf = json.loads((src / "run_manifest.json").read_text()) if (src / "run_manifest.json").exists() else {}
    if run_mf:
        for field, cli in (("seed", args.seed), ("scale", args.scale)):
            if run_mf.get(field) is not None and run_mf[field] != cli:
                print(f"  WARN: run_manifest {field}={run_mf[field]} != CLI --{field}={cli}; "
                      f"recording the ACTUAL run value {run_mf[field]}")

    # copy the packs used. The eval held-out packs are NOT training inputs and are NOT shipped
    # (shipping them would let anyone reconstruct the eval set). Kept only as manifest metadata.
    held = EVAL_HOLDOUT | {s.strip() for s in args.held_out.split(",") if s.strip()}
    packs_dst = dest / "packs"
    packs_dst.mkdir(exist_ok=True)
    pack_manifest = []
    for p in sorted(Path(args.packs).glob("*.json")):
        pk = json.loads(p.read_text())
        if pk.get("lang", "en") != args.lang:  # single-language snapshot
            continue
        slug = pk.get("slug", p.stem)
        is_held = slug in held
        if not is_held:  # do not ship eval-domain packs into the published snapshot
            shutil.copy2(p, packs_dst / p.name)
        pack_manifest.append({"slug": slug, "file": p.name if not is_held else None,
                              "entities": len(pk.get("entities", [])),
                              "docs": len(pk.get("docs", [])),
                              "held_out": is_held, "shipped": not is_held,
                              "sha256_12": sha12(p)})

    stats = {}
    if not args.no_tokens and (dest / "sft_train.jsonl").exists():
        print("computing token stats...", flush=True)
        stats = {"train": token_stats(dest / "sft_train.jsonl", args.model)}

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    # Provenance comes from the generator's run-manifest when present (what ACTUALLY ran), not CLI.
    prov_seed = run_mf.get("seed", args.seed)
    prov_scale = run_mf.get("scale", args.scale)
    prov_teacher = run_mf.get("model", args.teacher)
    manifest = {
        # dataset & model share one version label — this dataset trains exactly this model
        "version": args.version, "model_gguf": f"{args.model_name}-{args.version}",
        "lang": args.lang,
        "generated": generated, "model_id": args.model,
        "teacher": prov_teacher, "scale": prov_scale, "seed": prov_seed,
        "held_out": sorted(held), "note": args.note,
        "files": files, "packs": pack_manifest, "token_stats": stats,
        "run_manifest": run_mf or None,  # full generator provenance (hashes, teacher health, counts)
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2))

    n_train = files.get("sft_train.jsonl", {}).get("lines", "?")
    n_eval = files.get("sft_eval.jsonl", {}).get("lines", "?")
    n_raw = files.get("raw_generated.jsonl", {}).get("lines", "?")
    card = DATASET_CARD.format(
        version=args.version, model_id=args.model, teacher=args.teacher, lang=args.lang,
        model_gguf=f"{args.model_name}-{args.version}",
        held_out=args.held_out, n_train=n_train, n_eval=n_eval, n_raw=n_raw,
        scale=args.scale, seed=args.seed, generated=generated,
        note=f"- note: {args.note}" if args.note else "")
    (dest / "README.md").write_text(card)

    print(f"\nSnapshot -> {dest}")
    print(f"  train={n_train} eval={n_eval} raw={n_raw} packs={len(pack_manifest)} "
          f"(held-out: {', '.join(sorted(held)) or 'none'})")
    if stats:
        t = stats["train"]
        print(f"  train tokens: {t['total_tokens']:,} (mean {t['mean_tokens']}, "
              f"p95 {t['p95']}, max {t['max']})")
    print("\nTo PUBLISH (manual — do NOT automate):")
    print(f"  huggingface-cli upload <user>/webshop-agent-sft-{args.version} {dest} "
          f"--repo-type dataset")


if __name__ == "__main__":
    main()
