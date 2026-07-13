"""Judge bake-off: re-judge dumped eval trajectories with several LOCAL judge models and compare.

The main eval (`eval_generic.py --judge <model>`) writes `*_traj_<quant>.jsonl` trajectory dumps. This
re-judges those SAME responses with each candidate model (no re-running the student), so we can pick
the judge whose verdicts+reasons are soundest. 1.2B-Thinking fits all 3 ollama instances (parallel);
8B-A1B fits one (serial). Set OLLAMA_HOST to the round-robin endpoint.

Usage:
  OLLAMA_HOST=http://ollama.localhost:8080 uv run python scripts/judge_compare.py \
    reports/eval_nat_traj_Q6_K.jsonl \
    --judges hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 \
             hf.co/LiquidAI/LFM2.5-1.2B-Thinking-GGUF:Q8_0 \
             hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q8_0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kbft.teacher import Teacher
from pydantic import BaseModel

from scripts.eval_generic import _KIND_EXPECT


class JV(BaseModel):
    correct: bool
    natural: bool
    faithful: bool
    reason: str


SYS = ("You are a STRICT but FAIR evaluator of a shopping-assistant AI. Judge ONLY what the assistant "
       "actually did, against the expected behavior. Strict: robotic/garbled/empty replies are NOT "
       "natural; invented facts are NOT faithful; a wrong action is NOT correct.")


def _prompt(rec: dict) -> str:
    actions = "; ".join(f"{c[0]}({c[1]})" for c in rec["calls"]) or "(no tool calls)"
    expect = _KIND_EXPECT.get(rec["kind"], _KIND_EXPECT["_default"])
    return (f"EXPECTED BEHAVIOR: {expect}\n\nUSER TURNS: {' || '.join(rec['users'])}\n"
            f"ASSISTANT TOOL ACTIONS: {actions}\nASSISTANT FINAL REPLY: {rec['final'] or '(empty)'}\n\n"
            f"Rate correct / natural / faithful (faithful = true if it made no factual claims), "
            f"with a one-line reason.")


def judge_all(model: str, recs: list[dict], workers: int) -> list[dict | None]:
    t = Teacher(provider="ollama", model=model, workers=workers)
    return t.parallel_map(lambda r: t.chat_json(SYS, _prompt(r), JV, temperature=0.0), recs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("traj", help="a *_traj_*.jsonl dump from eval_generic --judge")
    ap.add_argument("--judges", nargs="+", required=True, help="ollama model ids to compare")
    ap.add_argument("--workers", type=int, default=6, help="parallelism (drop to 1 for a single-instance 8B)")
    ap.add_argument("--out", default="reports/judge_bakeoff.json")
    args = ap.parse_args()

    recs = [json.loads(l) for l in open(args.traj)]
    print(f"{len(recs)} trajectories from {args.traj}\n")

    per_model: dict[str, list[dict | None]] = {}
    for m in args.judges:
        # 8B fits ONE instance -> serialize (workers 1); small models fan out across the 3 instances.
        w = 1 if "8B" in m else args.workers
        verds = judge_all(m, recs, w)
        per_model[m] = verds
        agg = {k: [0, 0] for k in ("correct", "natural", "faithful")}
        for v in verds:
            if not isinstance(v, dict):
                continue
            for k in agg:
                agg[k][0] += int(bool(v.get(k)))
                agg[k][1] += 1
        line = " ".join(f"{k}={a}/{b}={a/b:.0%}" if b else f"{k}=-" for k, (a, b) in agg.items())
        errs = sum(1 for v in verds if not isinstance(v, dict))
        print(f"{m.split('/')[-1]:42s} {line}  (parse_errors={errs})")

    # pairwise agreement on `correct` (aligned by index; parallel_map preserves order)
    models = args.judges
    if len(models) > 1:
        print("\npairwise agreement on `correct`:")
        for i in range(len(models)):
            for j in range(i + 1, len(models)):
                a, b = per_model[models[i]], per_model[models[j]]
                both = [(x, y) for x, y in zip(a, b) if isinstance(x, dict) and isinstance(y, dict)]
                agree = sum(1 for x, y in both if bool(x.get("correct")) == bool(y.get("correct")))
                print(f"  {models[i].split('/')[-1]:30s} vs {models[j].split('/')[-1]:30s} "
                      f"{agree}/{len(both)}={agree/len(both):.0%}" if both else "  (no overlap)")

    # dump full verdicts+reasons for manual inspection (which judge REASONS soundly)
    out = {m: [{"name": r["name"], "kind": r["kind"], "verdict": v} for r, v in zip(recs, per_model[m])]
           for m in models}
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\nfull verdicts+reasons -> {args.out}")


if __name__ == "__main__":
    main()
