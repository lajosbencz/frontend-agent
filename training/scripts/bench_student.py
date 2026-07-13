"""Benchmark the fine-tuned student GGUFs: latency/throughput per quant level, CPU and GPU.

Reports prompt-eval (prefill) and generation tokens/sec plus model size for each quant on BOTH
backends via the vendored llama-bench: CPU (-ngl 0, the WASM-browser worst case) and GPU (-ngl 99,
Vulkan — the WebGPU-capable upper bound). Size × speed × the eval fidelity (eval_generic.py) picks
the shipping quant.

Usage:
  uv run python scripts/bench_student.py --gguf ../demo/public/models/lfm2.5-230m-v5-Q8_0.gguf ... \
      --out reports/bench_v5.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kbft.gguf_runtime import model_quant_label

REPO = Path(__file__).resolve().parents[1]
BENCH = REPO / "vendor" / "llama.cpp" / "build" / "bin" / "llama-bench"


def bench_one(gguf: str, n_prompt: int, n_gen: int, threads: int, reps: int, ngl: int) -> dict:
    """Run llama-bench on one backend (ngl layers on GPU) -> pp (prefill) & tg (gen) tokens/sec."""
    cmd = [str(BENCH), "-m", gguf, "-p", str(n_prompt), "-n", str(n_gen),
           "-t", str(threads), "-r", str(reps), "-ngl", str(ngl), "-o", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return {"pp_tps": None, "tg_tps": None, "error": res.stderr.strip()[-200:]}
    out = {"pp_tps": None, "tg_tps": None}
    for row in json.loads(res.stdout):
        # n_prompt>0 & n_gen==0 => prefill row; n_gen>0 & n_prompt==0 => generation row
        if row.get("n_prompt") and not row.get("n_gen"):
            out["pp_tps"] = round(row["avg_ts"], 2)
        elif row.get("n_gen") and not row.get("n_prompt"):
            out["tg_tps"] = round(row["avg_ts"], 2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", nargs="+", required=True)
    ap.add_argument("--n-prompt", type=int, default=512, help="prefill token count")
    ap.add_argument("--n-gen", type=int, default=128, help="generation token count")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--backends", nargs="+", default=["cpu", "gpu"], choices=["cpu", "gpu"])
    ap.add_argument("--out", default=str(REPO / "reports" / "bench.json"))
    args = ap.parse_args()

    if not BENCH.exists():
        raise SystemExit(f"llama-bench not built at {BENCH}")

    ngl = {"cpu": 0, "gpu": 99}
    report = {"threads": args.threads, "n_prompt": args.n_prompt, "n_gen": args.n_gen,
              "backends": args.backends, "quants": {}}
    for gguf in args.gguf:
        qlabel = model_quant_label(Path(gguf).name)
        size_mb = round(Path(gguf).stat().st_size / 1e6, 1)
        print(f"benchmarking {qlabel} ({size_mb} MB)...", flush=True)
        entry = {"size_mb": size_mb, "file": Path(gguf).name}
        for be in args.backends:
            res = bench_one(gguf, args.n_prompt, args.n_gen, args.threads, args.reps, ngl[be])
            entry[be] = res
            note = f" ({res['error']})" if res.get("error") else ""
            print(f"  {qlabel} [{be}]: prefill {res['pp_tps']} tok/s, gen {res['tg_tps']} tok/s{note}")
        report["quants"][qlabel] = entry

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {outp}")


if __name__ == "__main__":
    main()
