"""Convert a fine-tuned HF checkpoint to GGUFs for the browser, across quant levels.

Path: HF checkpoint -> f16 base GGUF (convert_hf_to_gguf) -> llama-quantize down to each target
(Q8_0 / Q6_K / Q4_K_M). The f16 base is an intermediate (kept in artifacts, not shipped); only the
quantized GGUFs land in the demo's models dir. K-quants (Q6_K/Q4_K_M) REQUIRE llama-quantize —
convert_hf_to_gguf can only emit f16/bf16/q8_0 — which is why the vendored llama.cpp is built.

Naming is generic (not domain-specific): {name}-{QUANT}.gguf. Bump --name per retrain so the
browser's OPFS cache fetches fresh weights.

Usage:
  uv run python scripts/export_gguf.py --checkpoint artifacts/full-230m \
      --name lfm2.5-230m-v5 --outdir ../demo/public/models --quants q8_0,q6_k,q4_k_m
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LLAMA = REPO / "training" / "vendor" / "llama.cpp"
CONVERTER = LLAMA / "convert_hf_to_gguf.py"
QUANTIZE = LLAMA / "build" / "bin" / "llama-quantize"

# llama-quantize type name per requested quant (case-insensitive input).
QUANT_TYPES = {"q8_0": "Q8_0", "q6_k": "Q6_K", "q5_k_m": "Q5_K_M", "q4_k_m": "Q4_K_M"}


def run(cmd: list[str]) -> None:
    print("Running:", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", default=str(REPO / "training" / "artifacts" / "full-230m"))
    p.add_argument("--name", default="lfm2.5-230m", help="base filename (no quant suffix/ext)")
    p.add_argument("--outdir", default=str(REPO / "demo" / "public" / "models"))
    p.add_argument("--quants", default="q8_0,q6_k,q4_k_m", help="comma-separated quant levels")
    p.add_argument("--f16", default=str(REPO / "training" / "artifacts" / "gguf" / "_f16_base.gguf"),
                   help="intermediate f16 GGUF (not shipped)")
    p.add_argument("--keep-f16", action="store_true", help="don't delete the f16 base after quantizing")
    args = p.parse_args()

    if not QUANTIZE.exists():
        sys.exit(f"llama-quantize not found at {QUANTIZE} — build it: "
                 f"cmake --build {LLAMA}/build --target llama-quantize")

    quants = [q.strip().lower() for q in args.quants.split(",") if q.strip()]
    bad = [q for q in quants if q not in QUANT_TYPES]
    if bad:
        sys.exit(f"unknown quant(s) {bad}; choose from {list(QUANT_TYPES)}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    f16 = Path(args.f16)
    f16.parent.mkdir(parents=True, exist_ok=True)

    # 1) HF -> f16 base (single conversion, reused for every quant)
    run([sys.executable, str(CONVERTER), args.checkpoint, "--outfile", str(f16), "--outtype", "f16"])

    # 2) f16 -> each quant
    produced = []
    for q in quants:
        out = outdir / f"{args.name}-{QUANT_TYPES[q]}.gguf"
        run([str(QUANTIZE), str(f16), str(out), QUANT_TYPES[q]])
        size_mb = out.stat().st_size / 1e6
        produced.append((out, size_mb))
        print(f"  -> {out.name} ({size_mb:.0f} MB)", flush=True)

    if not args.keep_f16:
        f16.unlink(missing_ok=True)

    print("\nExported:")
    for out, mb in produced:
        print(f"  {out}  ({mb:.0f} MB)")


if __name__ == "__main__":
    main()
