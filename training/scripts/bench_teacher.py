"""Bench a teacher model for the compositional pipeline: speed, JSON adherence, sample quality.

Runs a fixed batch of prompts covering the main recipe shapes (long-doc QA, varied add phrasings,
grounded comparison, multi-turn session) through the given Ollama model and reports:
  - rate (calls/sec) — speed, the whole point of a smaller teacher
  - json_ok/total — schema adherence (low = many graceful-skips = data loss)
  - one sample per shape — eyeball prose quality

Usage: uv run python scripts/bench_teacher.py --model qwen3.5:4b-q4_K_M [--reps 3]
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.brewcraft.config import build
from pydantic import BaseModel

from kbft.generic_gen import GEN_SYS
from kbft.teacher import QA_SCHEMA, UA_SCHEMA, Teacher


class _Step(BaseModel):
    user: str
    assistant: str


class SESSION_SCHEMA(BaseModel):
    steps: list[_Step] = []


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--reps", type=int, default=3)
    args = p.parse_args()

    cfg = build()
    kb = cfg.adapter.ingest()
    doc = next(d for d in kb.docs if d.id == "maintenance-descaling")
    e = kb.entities[:2]
    plan = (f"Step 1: shopper asks about the {e[0].title}. Step 2: shopper asks to add 2 of the "
            f"{e[1].title}. Step 3: shopper asks to go to checkout.")
    prompts = [
        ("qa", f"Article '{doc.title}':\n\n{doc.body}\n\nWrite 5 pairs: 'q' an info question "
               f"answerable from this; 'a' answers it directly from the article.", QA_SCHEMA, ("q", "a")),
        ("add", f"The shopper wants to add the '{e[0].title}'. Write 4 varied pairs: 'user' a casual "
                f"request to add it (each different); 'answer' confirms.", UA_SCHEMA, ("user", "answer")),
        ("cmp", f"Two products — {e[0].title} ${e[0].price}; {e[1].title} ${e[1].price}. Write 3 pairs: "
                f"'user' asks which to pick; 'answer' compares grounded ONLY in these facts.",
         UA_SCHEMA, ("user", "answer")),
        ("session", f"Write a BrewCraft chat as ONE coherent conversation, one user + one assistant "
                    f"reply per step:\n{plan}\nReturn JSON with a 'steps' array of {{user, assistant}}.",
         SESSION_SCHEMA, ("steps",)),
    ]

    t = Teacher(model=args.model, workers=8)
    t.chat_json("x", "Write 1 pair: user says hi; answer greets.", UA_SCHEMA)  # warmup / load

    def run(pr):
        kind, prompt, schema, keys = pr
        try:
            out = t.chat_json(GEN_SYS, prompt, schema, temperature=0.9)
        except Exception:  # noqa: BLE001
            return (kind, False, "")
        if keys == ("steps",):
            items = out.get("steps") if isinstance(out, dict) else (out if isinstance(out, list) else [])
            items = [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []
            ok = len(items) >= 1 and all(items[0].get(x) for x in ("user", "assistant"))
        else:
            items = out if isinstance(out, list) else (out.get("items", []) if isinstance(out, dict) else [])
            items = [x for x in items if isinstance(x, dict)]
            ok = len(items) >= 1 and all(items[0].get(x) for x in keys)
        return (kind, ok, json.dumps(items[0]) if items else "")

    jobs = prompts * args.reps
    s = time.time()
    results = t.parallel_map(run, jobs)
    dt = time.time() - s
    results = [r for r in results if isinstance(r, tuple)]
    ok = sum(1 for _, o, _ in results if o)
    print(f"\n=== {args.model} ===")
    print(f"rate={len(jobs) / dt:.2f} calls/s | time={dt:.1f}s | json_ok={ok}/{len(jobs)}")
    seen = set()
    for kind, o, sample in results:
        if kind not in seen and sample:
            seen.add(kind)
            print(f"  [{kind}] {'OK ' if o else 'BAD'} {sample[:170]}")


if __name__ == "__main__":
    main()
