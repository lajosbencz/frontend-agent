"""Aggregate eval_generic.py + bench_student.py into a markdown MATRIX report (param size × quant).

Rows are configs keyed '{params}-{version}-{quant}' (e.g. 230m-v6-Q8_0). The ship pick is the
SMALLEST-download config whose held-out score is within --tol of the best-scoring config — i.e. the
cheapest browser payload that doesn't measurably sacrifice quality. Prior versions (e.g. v5) can be
included as baseline rows for reference.

Usage:
  uv run python scripts/report.py --eval reports/eval_v6.json --bench reports/bench_v6.json \
      --out reports/report_v6.md
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_QORD = {"Q4_K_M": 0, "Q4_K_S": 0, "Q5_K_M": 1, "Q6_K": 2, "Q8_0": 3}


def parse_key(k: str) -> tuple:
    """(param_millions, version_tuple, quant_rank) for sorting the matrix rows. Version is a tuple so
    both legacy 'v6' and dotted 'v0.7.0' sort correctly."""
    pm = re.search(r"(\d+)m", k)
    vm = re.search(r"v(\d+(?:\.\d+)*)", k)
    qm = re.search(r"(Q\d[A-Za-z0-9_]*)", k)
    ver = tuple(int(x) for x in vm.group(1).split(".")) if vm else (0,)
    return (int(pm.group(1)) if pm else 0, ver, _QORD.get(qm.group(1) if qm else "", 9))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True)
    ap.add_argument("--bench", default=None)
    ap.add_argument("--tol", type=float, default=0.015, help="max score drop vs best to still ship")
    ap.add_argument("--out", default=str(REPO / "reports" / "report.md"))
    args = ap.parse_args()

    ev = json.loads(Path(args.eval).read_text())
    bench = json.loads(Path(args.bench).read_text()) if args.bench else {"quants": {}}
    q = ev["quants"]
    keys = sorted(q, key=parse_key)

    best = max(q, key=lambda k: q[k]["score"])
    best_score = q[best]["score"]

    dim_order = ["tool_selection", "arg_binding", "id_grounded", "reference_track", "rag_faithful",
                 "refusal", "no_unsolicited_add", "compound_both", "search_before_add",
                 "total_correct", "navigate", "cart_preserved", "boundary",
                 "listing", "param_search", "comparison"]
    dims = [d for d in dim_order if any(d in q[k]["overall"] for k in q)]

    L = ["# Eval matrix — param size × quant × eval\n",
         f"Held-out (zero training data in these domains) · {ev['n_per_kind']} scenarios/kind/config · "
         f"backend ngl={ev.get('backend')}. Best config: **{best}** ({best_score:.1%}).\n",
         "## Fidelity matrix\n",
         "| config | size | overall | " + " | ".join(dims) + " |",
         "|" + "---|" * (3 + len(dims))]
    for k in keys:
        d = q[k]
        cells = []
        for dim in dims:
            if dim in d["overall"]:
                ok, n = d["overall"][dim]
                cells.append(f"{ok}/{n}")
            else:
                cells.append("—")
        delta = d["score"] - best_score
        dtag = "" if k == best else f" ({delta * 100:+.1f})"
        L.append(f"| **{k}** | {d['size_mb']:.0f}MB | {d['score']:.1%}{dtag} | " + " | ".join(cells) + " |")
    L.append("")

    if bench["quants"]:
        L.append("## Speed (llama-bench, tok/s)\n")
        L.append("| config | size | CPU prefill | CPU gen | GPU prefill | GPU gen |")
        L.append("|---|---|---|---|---|---|")
        for k in sorted(bench["quants"], key=parse_key):
            b = bench["quants"][k]
            cpu, gpu = b.get("cpu", {}), b.get("gpu", {})
            L.append(f"| **{k}** | {b.get('size_mb', '?')}MB | {cpu.get('pp_tps', '—')} | "
                     f"{cpu.get('tg_tps', '—')} | {gpu.get('pp_tps', '—')} | {gpu.get('tg_tps', '—')} |")
        L.append("")

    # ship pick: smallest download within tolerance of the best score
    eligible = [k for k in q if best_score - q[k]["score"] <= args.tol]
    pick = min(eligible, key=lambda k: q[k]["size_mb"])
    L.append("## Recommendation\n")
    L.append(f"**Ship `{pick}`** ({q[pick]['size_mb']:.0f}MB, {q[pick]['score']:.1%}) — the smallest "
             f"download within {args.tol * 100:.1f} pts of the best ({best}, {best_score:.1%}).\n")
    for k in keys:
        drop = (best_score - q[k]["score"]) * 100
        bq = bench["quants"].get(k, {})
        spd = bq.get("cpu", {}).get("tg_tps")
        spd_s = f", {spd} tok/s CPU" if spd else ""
        verdict = "✓ within tol" if drop <= args.tol * 100 else "too lossy"
        L.append(f"- `{k}`: {q[k]['score']:.1%} ({drop:+.1f} vs best; {q[k]['size_mb']:.0f}MB{spd_s}) — {verdict}")
    L.append("")

    # Regression gate: the ship pick must not drop >5 pts on ANY dimension vs the single best prior
    # model OF THE SAME PARAM SIZE — the champion it is replacing. NOT a per-dim max across configs
    # (an unachievable union that no single model hits -> false flags), and NOT across param sizes
    # (a 230M "regressing" vs a 350M is meaningless). Guards against the aggregate masking a
    # per-dimension capability collapse (one dim craters while the overall score stays flat).
    def _ver(k: str) -> tuple:
        return parse_key(k)[1]

    def _size(k: str) -> int:
        return parse_key(k)[0]

    cur_ver = max(_ver(k) for k in q)
    pick_size = _size(pick)
    prior_same = [k for k in q if _ver(k) < cur_ver and _size(k) == pick_size]
    prior_any = [k for k in q if _ver(k) < cur_ver]
    L.append("## Regression gate\n")
    if not prior_any:
        L.append("No prior-version configs in this matrix — nothing to compare against.\n")
    else:
        # the champion = best prior model of the SAME size (fall back to any size, flagged, if none)
        ref_pool = prior_same or prior_any
        ref = max(ref_pool, key=lambda k: q[k]["score"])
        note = "" if prior_same else " (no same-size prior — comparing across param sizes)"

        def dim_pct(k: str, dim: str):
            ok, n = q[k]["overall"].get(dim, (0, 0))
            return (ok / n) if n else None

        regressions = []
        for dim in dims:
            pk = dim_pct(pick, dim)
            rf = dim_pct(ref, dim)
            if pk is None or rf is None:
                continue
            if pk < rf - 0.05:
                regressions.append((dim, pk, rf))
        if regressions:
            L.append(f"⚠️ **{len(regressions)} regression(s)** in ship pick `{pick}` vs the champion "
                     f"`{ref}`{note} (>5 pts) — do NOT ship on the aggregate:\n")
            for dim, pk, rf in regressions:
                L.append(f"- `{dim}`: {pk:.0%} vs `{ref}` {rf:.0%} ({(pk - rf) * 100:+.0f} pts)")
        else:
            L.append(f"✓ No per-dimension regression >5 pts in ship pick `{pick}` vs the champion "
                     f"`{ref}`{note}.")
        L.append("")

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(L))
    print("\n".join(L))
    print(f"\nWrote {outp}")


if __name__ == "__main__":
    main()
