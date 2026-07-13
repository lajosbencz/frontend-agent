"""Driver: generate the generic, multi-pack, RAG-grounded SFT dataset.

Iterates every clean pack (data/packs/*.json), runs the generic recipes per pack, renders with the
frozen generic tool schema, and dumps one merged train/eval split. Held-out packs (the demo domain)
are excluded via --hold-out. Crash-safe: each pack's renders are appended to raw_generated.jsonl.

Usage: uv run python scripts/generate_generic.py [--scale 1] [--hold-out espresso] [--only books,pet]
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transformers import AutoTokenizer

from kbft.adapters.pack import PackAdapter, load_all_packs
from kbft.generic_gen import GENERIC_RECIPES, GenConfig, GenCounts, PackCtx
from kbft.holdout import EVAL_HOLDOUT, assert_no_leakage
from kbft.render import RAW_FILE, dedup_split, dump_rendered
from kbft.teacher import Teacher
from kbft.train_config import TrainingConfig

REPO = Path(__file__).resolve().parents[1]
PACK_DIR = REPO / "data" / "packs"
OUT_DIR = REPO / "data" / "dataset"

# Default teacher/judge rosters. Teacher is TIERED by output-schema complexity: tier 0 (simple single-
# string surface — user utterances / one grounded answer) → local ollama 1.2B; tier 1 (coupled multi-
# field schemas a small model garbles) → OpenRouter flash+flash-lite load-balanced. Judge = deepseek
# (a different family). Drop the tier-0 member (or add more) for an all-cloud or richer roster.
DEFAULT_TEACHER_ROSTER = (
    '[{"tier":0,"weight":1,"provider":"ollama","model":"hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q8_0"},'
    '{"tier":1,"weight":1,"provider":"openrouter","model":"google/gemini-2.5-flash"},'
    '{"tier":1,"weight":1,"provider":"openrouter","model":"google/gemini-2.5-flash-lite"}]')
DEFAULT_VERIFIER_ROSTER = '[{"weight":1,"provider":"openrouter","model":"deepseek/deepseek-v4-flash"}]'


def _guard_gpu_contention(allow: bool) -> None:
    """Teacher generation loads a model onto the shared 16GB GPU. Running it CONCURRENT with a train
    OOM'd the card before (incident-a). Refuse if a train.py is running, unless explicitly allowed."""
    if allow:
        return
    import subprocess
    try:
        out = subprocess.run(["pgrep", "-af", "scripts/train.py"], capture_output=True, text=True)
        running = [ln for ln in out.stdout.splitlines() if "pgrep" not in ln]
    except FileNotFoundError:
        running = []
    if running:
        raise SystemExit("REFUSING: a training run appears active (scripts/train.py) — teacher "
                         "generation would load onto the shared GPU and risk OOM. Wait for it to "
                         "finish, or pass --allow-concurrent-train if you know the GPU has room.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", default=str(PACK_DIR))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--scale", type=int, default=1)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--pack-workers", type=int, default=1,
                    help="generate this many packs CONCURRENTLY — fills the idle GPU/cloud gaps between "
                         "per-recipe barriers (a single pack leaves the fast tier idle waiting on cloud "
                         "calls). Total concurrency ~= pack_workers * workers; keep the product ~20-40. "
                         "Deterministic: each pack uses its own seeded rng, so completion order is moot.")
    ap.add_argument("--hold-out", default="", help="comma-separated pack slugs to exclude (demo domain)")
    ap.add_argument("--only", default="", help="comma-separated pack slugs to limit to")
    ap.add_argument("--recipes", default="", help="comma-separated recipe names to run (default all); "
                    "use to regenerate a subset, e.g. only the deterministic action recipes (no teacher)")
    ap.add_argument("--sessions", type=int, default=0, help="also generate N composed multi-intent "
                    "sessions per pack via the semi-random state machine (kbft/session_sim.py)")
    ap.add_argument("--lang", default="en",
                    help="train ONE language per run (no mixing): only packs whose 'lang' matches "
                         "are included. A model is trained per-language.")
    ap.add_argument("--seed", type=int, default=20260707)
    ap.add_argument("--max-len", type=int, default=TrainingConfig.model_fields["max_len"].default,
                    help="warn on examples over this many tokens (defaults to TrainingConfig.max_len)")
    ap.add_argument("--allow-concurrent-train", action="store_true",
                    help="skip the guard that refuses to run the teacher while a train.py is active")
    ap.add_argument("--verify-grounding", action="store_true",
                    help="faithfulness gate: a verifier LLM confirms each grounded answer is supported "
                         "by the injected results (rejects hallucinations). Adds one verifier call per "
                         "grounded answer — use a STRONG verifier (gemini-2.5-flash class); lightweight "
                         "models wave hallucinations through.")
    ap.add_argument("--teacher-roster", default=DEFAULT_TEACHER_ROSTER, help='teacher config: inline '
                    'JSON or a path to a .json file; each member = {tier,weight,provider,model}. '
                    'Members are grouped by `tier` (int) — a call routes to the tier matching its '
                    'output-schema complexity (0=simple single-string, 1=coupled/multi-field); within '
                    'a tier, `weight` (int) is a weighted-fallback pool (0=fallback-only). PER-MEMBER '
                    'provider (mix ollama+openrouter). Single tier = a bare pool (no routing).')
    ap.add_argument("--verifier-roster", default=DEFAULT_VERIFIER_ROSTER,
                    help="same shape as --teacher-roster, for the faithfulness judge (used with "
                         "--verify-grounding). Keep it a DIFFERENT family than the teacher (avoid bias).")
    args = ap.parse_args()

    import json as _cfgjson
    def _parse_roster(spec: str):
        """A roster is inline JSON or a path to a JSON file → list of {weight,provider,model} dicts."""
        if not spec:
            return None
        roster = _cfgjson.loads(Path(spec).read_text() if Path(spec).exists() else spec)
        if not roster:
            raise SystemExit("empty teacher/verifier roster")
        return roster
    teacher_roster = _parse_roster(args.teacher_roster)
    verifier_roster = _parse_roster(args.verifier_roster)

    # OpenRouter runs remotely — no local GPU contention, so the guard only applies to ollama.
    _providers = {e["provider"] for e in teacher_roster + (verifier_roster or [])}
    _guard_gpu_contention(args.allow_concurrent_train or _providers <= {"openrouter"})

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # FAIL-CLOSED: the eval held-out domains are ALWAYS excluded (single source of truth in
    # kbft.holdout), regardless of the CLI flag — the flag can only add MORE exclusions, never
    # re-admit an eval domain. Post-generation we also VERIFY absence (assert_no_leakage below).
    hold = EVAL_HOLDOUT | {s.strip() for s in args.hold_out.split(",") if s.strip()}
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    # Single-language datasets only: a run selects one language, so the resulting model is monolingual.
    packs = [p for p in load_all_packs(args.packs)
             if p.get("lang", "en") == args.lang
             and p["slug"] not in hold and (not only or p["slug"] in only)]
    if not packs:
        raise SystemExit(f"no packs for lang={args.lang!r} (available langs: "
                         f"{sorted({p.get('lang', 'en') for p in load_all_packs(args.packs)})})")
    print(f"[lang={args.lang}] {len(packs)} packs: {', '.join(p['slug'] for p in packs)}"
          + (f"  (held out: {', '.join(sorted(hold))})" if hold else ""))

    rset = {s.strip() for s in args.recipes.split(",") if s.strip()}
    recipes = [r for r in GENERIC_RECIPES if not rset or r.__name__ in rset]
    if rset:
        print(f"recipes subset ({len(recipes)}): {', '.join(r.__name__ for r in recipes)}")

    from collections import defaultdict

    from kbft.tiered import PoolTeacher, TieredTeacher

    def _roster_pool(members):
        """Weighted-fallback PoolTeacher from roster members (PER-MEMBER provider; weight 0 = fallback)."""
        ts = [Teacher(provider=e["provider"], model=e["model"], workers=args.workers, seed=args.seed)
              for e in members]
        return ts[0] if len(ts) == 1 else PoolTeacher(ts, [int(e.get("weight", 1)) for e in members])

    def _build_teacher(roster):
        """Group roster by `tier` → one weighted pool per tier → TieredTeacher (routes each call to a
        tier by output-schema complexity). A single tier collapses to a bare pool (no routing)."""
        by_tier = defaultdict(list)
        for e in roster:
            by_tier[int(e.get("tier", 0))].append(e)
        if len(by_tier) == 1:
            return _roster_pool(next(iter(by_tier.values())))
        return TieredTeacher({t: _roster_pool(ms) for t, ms in by_tier.items()})

    teacher = _build_teacher(teacher_roster)
    print(f"teacher: {teacher.model}")
    verifier = _roster_pool(verifier_roster) if args.verify_grounding else None
    if verifier is not None:
        print(f"faithfulness gate ON — verifier: {verifier.model}")
    cfg = GenConfig(teacher=teacher, counts=GenCounts(),
                    verify_grounding=args.verify_grounding, verifier=verifier)
    tok = AutoTokenizer.from_pretrained(cfg.model_id)
    rng = random.Random(args.seed)

    import hashlib
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from kbft.session_sim import simulate_sessions

    rendered: list[dict] = []
    counters = {"skipped": 0, "overflow": 0, "max_tok": 0}
    dump_lock = threading.Lock()  # rendered list, raw file, and the (non-thread-safe) tokenizer
    raw = open(out / RAW_FILE, "w")

    def run_pack(job: tuple[int, dict]) -> None:
        p, pack = job
        # Per-(pass,pack) rng so CONCURRENT packs don't race on one generator — deterministic and
        # order-invariant (a pack's output depends only on its slug+pass, not on completion order).
        prng = random.Random(f"{args.seed}:{p}:{pack['slug']}")
        # ~half the packs get hyphenated slug ids (like the demo) so the model learns to copy the FULL
        # id verbatim from results, not truncate to the query word. Deterministic.
        sem = int(hashlib.md5(pack["slug"].encode()).hexdigest(), 16) % 2 == 0
        kb = PackAdapter(pack, semantic_ids=sem).ingest()
        ctx = PackCtx(pack, kb, cfg, prng)  # aliases tools per pack/pass
        exs = []
        for recipe in recipes:
            exs.extend(recipe(ctx))
        if args.sessions:  # composed multi-intent sessions (semi-random state machine)
            exs.extend(simulate_sessions(ctx, args.sessions, args.seed + p))
        with dump_lock:  # render with THIS pack's aliased tool schema so calls match the injected tools
            s, o, mx = dump_rendered(exs, tok, ctx.tools, rendered, raw, max_len=args.max_len)
            counters["skipped"] += s
            counters["overflow"] += o
            counters["max_tok"] = max(counters["max_tok"], mx)
            print(f"  pass {p + 1}/{args.scale} [{pack['slug']}]: {len(exs)} examples "
                  f"({len(rendered)} total)", flush=True)

    jobs = [(p, pack) for p in range(args.scale) for pack in packs]
    print(f"generating {len(jobs)} (pass,pack) jobs, {args.pack_workers} concurrent")
    with ThreadPoolExecutor(max_workers=args.pack_workers) as pool:
        list(pool.map(run_pack, jobs))
    raw.close()
    skipped, overflow, max_tok = counters["skipped"], counters["overflow"], counters["max_tok"]
    # canonical order so the seeded dedup/shuffle split is deterministic despite concurrent completion.
    rendered.sort(key=lambda r: r["text"])
    if skipped:
        print(f"  skipped {skipped} malformed")
    # length guard: warn if any example exceeds the training max_len (the trainer truncates it).
    print(f"[guard] max example length: {max_tok} tokens (max_len={args.max_len})")
    if overflow:
        print(f"[guard] WARNING: {overflow} example(s) exceed max_len={args.max_len} and will be "
              f"truncated at train time — shorten sessions or raise max_len if this share is large")
    stats = dedup_split(rendered, out, rng, eval_frac=12)

    # --- P0 gates: verify loudly instead of trusting the run went fine ---
    # (1) held-out leakage: hard-fail if any eval-domain id reached the train file.
    checked = assert_no_leakage(out / "sft_train.jsonl", args.packs)
    print(f"[gate] leakage check OK: 0 of {checked} held-out ids in sft_train.jsonl "
          f"(excluded domains: {', '.join(sorted(hold))})")
    # (2) teacher health: abort if the teacher silently failed on a large share of jobs (which would
    # hollow out whole recipe classes). Threshold is generous; the point is to never ship blind.
    rate = teacher.failure_rate()
    print(f"[gate] teacher: {teacher.calls} calls, {teacher.failures} failures ({rate:.1%})")
    if rate > 0.15:
        raise SystemExit(f"teacher failure rate {rate:.1%} exceeds 15% — dataset would be "
                         f"distribution-skewed; aborting. Check the model/endpoint.")
    if verifier is not None:
        vchecks = verifier.calls
        vrej = verifier.rejections
        vrate = (vrej / vchecks) if vchecks else 0.0
        print(f"[gate] faithfulness verifier: {vchecks} checks, {vrej} rejected ({vrate:.1%}), "
              f"{verifier.failures} verifier errors")
        if vrate > 0.30:
            print(f"[gate] WARNING: verifier rejected {vrate:.0%} of grounded answers — either the "
                  f"teacher is hallucinating a lot or the verifier is too strict. Inspect before trusting.")
    # (3) run-manifest: record what ACTUALLY ran (real args + input pack hashes + output hashes) so
    # snapshot ingests provenance and train can verify it — no CLI-supplied fiction.
    import hashlib as _hl
    import json as _json
    def _sha(path: Path) -> str:
        return _hl.sha256(path.read_bytes()).hexdigest()[:16]
    manifest = {
        "seed": args.seed, "scale": args.scale, "lang": args.lang,
        "teacher_roster": teacher_roster, "verifier_roster": verifier_roster,
        "held_out": sorted(hold), "packs": [p["slug"] for p in packs],
        "recipes": "all" if not rset else sorted(rset),
        "teacher_calls": teacher.calls, "teacher_failures": teacher.failures,
        "verify_grounding": args.verify_grounding,
        "verifier": ({"model": verifier.model, "checks": verifier.calls,
                      "rejections": verifier.rejections, "errors": verifier.failures}
                     if verifier is not None else None),
        "counts": {"train": stats.get("train"), "eval": stats.get("eval")} if isinstance(stats, dict) else None,
        "sha": {"sft_train.jsonl": _sha(out / "sft_train.jsonl"),
                "sft_eval.jsonl": _sha(out / "sft_eval.jsonl")},
        "pack_sha": {p["slug"]: _hl.sha256(_json.dumps(p, sort_keys=True).encode()).hexdigest()[:16]
                     for p in packs},
    }
    (out / "run_manifest.json").write_text(_json.dumps(manifest, indent=2))
    print(f"[gate] wrote {out / 'run_manifest.json'}")


if __name__ == "__main__":
    main()
