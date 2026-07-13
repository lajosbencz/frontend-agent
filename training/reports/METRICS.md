# Model metrics — cross-version tracking (EN generalist, LFM2.5-230M)

Held-out eval (zero training data in these domains): **brewcraft** (domain module) + **videogames**
(pack), n=6 scenarios/kind/config, 230M **Q8_0** unless noted. Source: `reports/report_v*_230q8.md`.
Higher = better. Dims are `correct/total`.

## Full matrix

| version | overall | tool_sel | arg_bind | id_grnd | ref_track | rag_faith | refusal | no_unsol_add | compound | search_b4_add | total_rd | navigate | cart_pres | boundary | listing | param_srch | comparison |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 230m-v0.7.0 | 82.9% | 115/154 | 304/315 | 46/72 | 17/18 | 20/28 | 64/82 | 24/24 | **0/24** | 21/24 | 18/24 | 24/24 | 22/24 | 28/28 | 5/18 | 18/18 | 16/18 |
| 230m-v0.9.0 | 89.4% | 122/154 | 307/307 | 67/72 | 17/18 | 14/28 | 66/82 | 24/24 | 15/24 | 20/24 | 22/24 | 24/24 | 23/24 | 28/28 | 13/18 | 18/18 | 13/18 |
| 230m-v0.9.1 | 90.4% | 124/154 | 317/317 | 67/72 | 18/18 | 18/28 | 68/82 | 24/24 | 18/24 | 22/24 | 21/24 | 24/24 | 24/24 | 28/28 | 6/18 | 18/18 | 14/18 |
| 230m-v0.9.2 | 90.2% | 129/154 | 323/323 | 67/72 | 14/18 | 19/28 | 66/82 | 24/24 | 20/24 | 21/24 | 20/24 | **11/24** | 22/24 | 28/28 | 17/18 | 18/18 | 16/18 |
| **230m-v0.9.3** | 91.9% | 128/154 | 321/321 | 65/72 | 18/18 | 17/28 | 70/82 | 23/24 | 18/24 | 20/24 | 20/24 | 24/24 | 24/24 | 28/28 | 18/18 | 18/18 | 16/18 |
| 230m-v0.9.4 | 93.1% | 149/154 | 346/347 | 56/72 | 16/18 | **21/28** | 78/82 | 22/24 | **13/24** | 22/24 | 20/24 | 24/24 | 23/24 | 24/28 | 17/18 | 18/18 | 14/18 |
| 230m-v0.9.5 | 91.8% | 147/154 | 345/347 | 61/72 | 13/18 | 16/28 | 78/82 | 22/24 | 17/24 | 19/24 | 19/24 | 24/24 | 22/24 | 24/28 | 15/18 | 18/18 | 11/18 |
| **230m-v0.9.6 → v1.0.0** | **95.2%** | **154/154** | **354/354** | **68/72** | 18/18 | 17/28 | 76/82 | 23/24 | 16/24 | 21/24 | 22/24 | 24/24 | 23/24 | 24/28 | 15/18 | 18/18 | 16/18 |
| 230m-v0.10.0 | 93.4% | 152/154 | 358/358 | 65/72 | 17/18 | 17/28 | 78/82 | 22/24 | 13/24 | 21/24 | 19/24 | 24/24 | 23/24 | 22/28 | 14/18 | 18/18 | 13/18 |
| 350m-v0.6.1 (Q4_K_M) | 82.9% | 100/154 | 290/295 | 43/72 | 12/18 | 18/28 | 66/82 | 24/24 | 23/24 | 23/24 | 22/24 | 24/24 | 23/24 | 28/28 | 0/18 | 18/18 | 14/18 |

## Per-version log (what changed → verdict)
- **v0.7.0** — first generic full regen. compound_both COLLAPSED 0/24 (stop-after-first-add). listing weak.
- **v0.9.0** — count rebalance + bulk_add/triple_add → compound 0→15, id 67. But rag over-trimmed (14/28).
- **v0.9.1** — +6000 zero-teacher grounding splice from v0.7.0 → rag 14→18, compound 18. listing crashed 6.
- **v0.9.2** — browse_overview listing boost → listing 6→17 BUT navigate COLLAPSED 24→11 (whack-a-mole).
- **v0.9.3** — balanced deterministic aug (browse+nav+ref together) → listing 18 AND nav 24 both fixed.
  **= the balanced-champion; no severe regressions.** (4b teacher; that's why tool_sel/arg only 128/321.)
- **v0.9.4** — clean-pipeline rebuild + **gemini-2.5-flash teacher** + kb_decisive 26 → rag BEST 21,
  tool_sel 149, arg 346. But kb_decisive 26 drowned compound (13) + id (56). GATED (compound collapse).
- **v0.9.5** — credit-free: +9058 deterministic compound/id/ref splice → compound 17, id 61. But diluted
  rag → rag CRASHED 16. GATED. (Proved: free splices only REDISTRIBUTE the compound↔rag balance.)
- **v0.9.6** — paid rebalanced full regen: kb_decisive 20 + compound intact + gemini-flash teacher →
  **NEW BEST 95.2%; tool_sel 154/154 & arg_bind 354/354 PERFECT, id 68 best.** rag held 17 (not 21),
  compound 16, boundary 24, listing 15. **Best-fundamentals ship candidate.**
- **v0.10.0** — credit-free copy of v0.9.6 + manual hand-designed deterministic tweaks (`kb_select`
  doc-selection + compound/listing boost, 5150 fresh, 0 teacher). **RESULT: 93.4%, a clean LOSS
  (-1.8).** Every target missed: rag 17→17 (ZERO movement), compound 16→13, listing 15→14, id 68→65,
  comparison 16→13. **Two durable proofs:** (1) `kb_select` not moving rag CONFIRMS rag_faithful is
  RETRIEVAL-limited (BM25 wrong doc), not doc-selection — the eval-ceiling diagnosis holds. (2) Free
  deterministic splices cannot recover paid-teacher NL quality; they only redistribute the frontier
  and here slid everything down. **v0.9.6 stays champion. The free-tweak lever is EXHAUSTED.**

## KEY LEARNINGS (durable)
- **compound↔rag is a Pareto tradeoff, ~linear in `kb_decisive` count:** kb16→rag17/comp18 (v0.9.3),
  kb20→rag17/comp16 (v0.9.6), kb26→rag21/comp13 (v0.9.4). Can't max both from that knob alone.
- **Teacher quality is the big orthogonal lever:** 4b→gemini-2.5-flash lifted tool_sel 128→154,
  arg 321→354, id/refusal — everything NOT on the compound↔rag axis.
- **Free splices redistribute, they don't dominate** — they slide along the frontier (v0.9.5 proof).
- **rag_faithful ~17/28 is partly an EVAL CEILING** (Goodhart): diag shows the model always searches +
  grounds faithfully; failures are the eval's BM25 returning the wrong doc + strict title-token match.
  The fixable slice = doc-SELECTION among distractors (→ the v0.10.0 kb_select tweak).
- **Regression gate must compare vs the same-size CHAMPION**, not a per-dim union (that gave 4 phantom
  flags). Fixed in report.py.
- **Whack-a-mole rule:** boosting one pattern drowns low-count ones — always reinforce the affected
  cluster TOGETHER, balanced.

## CURRENT STATE
- **SHIPPED: v1.0.0** = the v0.9.6 generation (95.2%) promoted verbatim to the first stable release
  (MAJOR bump; no retrain). Published as `lazos/lfm2.5-230m-frontend-agent` (bf16 + GGUF F16/Q8/Q6/Q4)
  + dataset `lazos/frontend-agent-sft` (synthetic subset, CC-BY-4.0).
- **v0.10.0 — rejected** (93.4%, credit-free tweaks lost). Free-tweak lever exhausted; further rag
  gains need a retrieval fix (Goodhart, not worth chasing) or a paid regen.
- Prior balanced champion v0.9.3 (91.9%) — alternative if compound/boundary/listing are weighted over
  the fundamentals.
- App demo serves **v1.0.0 Q6_K** (library default). Quant sweep on brewcraft (n=6,
  `reports/report_quant_compare.md`): **Q6_K 96.3% = Q8_0 96.2% > Q4_K_M 94.2%** — Q4 drops ~2pts
  (worse query formulation / grounding), so Q6_K is the quality/size sweet spot (191MB). The demo
  acceptance flow is guarded by `scripts/replay_chat.py` (headless replay of a real chat over the demo
  index; it also surfaced that a non-representative catalog hint — not the model — caused bad
  "what do you offer" answers, fixed in the RAG adapter's group-diverse `hint()`).
- HU/bonic track (v0.8.0) abandoned (bust); the `kbft/locales/` layer remains for future languages.

## Iteration 1 — fully-local-ish tiered teacher (UPDATED harness) — 2026-07-12 08:39 CEST
**NOT comparable to the table above** — harness changed: tool contract gained `search_catalog` facets
(category/min_price/max_price/in_stock/sort) + a `submit_form` tool, injected into EVERY scenario; +3
new dims (form_grounded, facet_stock, facet_sort); n=5. BOTH models re-scored on this harness, Q8_0,
held-out brewcraft(live)+videogames, canonical+aliased.

- **iter1** (`full-230m-iter1`): tiered teacher = LFM2.5-1.2B local (simple) + gemini-2.5-flash-lite
  (complex); 15,458 ex / 18.8M tok (10,476 gen + 4,982 flash `_cal` merged); full-fp32, ep 1.3, 2/8.
- **champion** = shipped v1.0.0 (gemini-flash teacher, 72M tok).

| model | OVERALL | vg/canon | vg/alias | brew/canon | brew/alias |
|---|---|---|---|---|---|
| **iter1** | **88.8%** (849/956) | 87% | **85%** | 93% | **92%** |
| champion v1.0.0 | 68.5% (657/959) | 88% | **49%** | 86% | **51%** |

**Verdict: iter1 >> champion on the current contract (+20.3%).** The win is NOT a facet cherry-pick:
on CANONICAL tools the two are ~equal (no classic regression); on ALIASED/arbitrary schemas champion
CRATERS to ~50% while iter1 holds 85-92% — champion lost schema-reading robustness on the larger
current contract; iter1 kept it (the project's core thesis). Plus new caps champion has zero of:
param_search 100/0, facet_sort 100/0, form_grounded 90/0. iter1 also ▲ on id_grounded (83/52),
tool_selection (95/52), reference_track (88/44), navigate (100/75), listing (75/38), rag_faithful
(71/54). champion ▲ only on refusal (94/83), no_unsolicited_add (100/85), comparison (44/38 tiny).
**One shared HOLE: facet_in_stock 0/0** — "in stock" phrasing absorbed into query, not the bool facet.

**Status: iter1 = leading candidate, NOT yet promoted to the shipped slot** (has the in_stock hole;
closing it via a targeted top-up before promotion). Reports: `eval_iter1.json`, `eval_champion_reeval.json`.

## Iteration 2 — in_stock facet top-up — REJECTED — 2026-07-12 09:29:34 CEST
Targeted top-up: +446 standalone-facet examples (faceted_search recipe fixed to independent optional
facets), 15,458→15,904 ex, in_stock coverage 0.6%→2.3%. Retrained iter2 (full-fp32 2/8).
**RESULT: iter2 87.4% < iter1 88.8% — a LOSS.** Target barely moved (facet_in_stock 0→2/16=12%) while
whack-a-mole hit the multi-turn cluster: compound 55→40%, id_grounded 83→72%, total_correct 60→35%,
listing 75→62%. Probe: model emits `search_catalog(query='accessories')` — OMITS in_stock; the
"search=query(+price)" prior dominates, 2.3% signal can't overcome it (vs `sort` which has an
unambiguous "sorted by" trigger). facet_in_stock is a weak-boolean-facet-vs-strong-prior problem +
partial eval over-strictness (plain search of stock-annotated items isn't wrong). **Not chased further.**
**iter1 remains leader.** iter2 GGUF/report kept: artifacts/gguf/iter2, reports/eval_iter2.json.

## Iteration 3 — scaled balanced regen (scale 4 + sessions 8, 27.2M tok) — REJECTED — 2026-07-12 11:20:05 CEST
Hypothesis: iter1 volume-thin on classic dims → more volume + multi-turn sessions lifts them.
**RESULT: iter3 87.3% < iter1 88.8% — a LOSS (redistribution, not improvement).** Big GAINS
(rag_faithful 71→88%, cart_preserved 70→90%, no_unsolicited_add 85→100%, form 90→100%, compound 55→60%)
paid for by big LOSSES (boundary 100→71%, comparison 38→19%, total_correct 60→45%, id 83→77%, refusal
83→75%). Sessions-8 raised cart-action density → more action-happy, hurt boundary/refusal honesty.
Confirms the METRICS-log rule: this plateau needs careful multi-dim BALANCING, not naive scale.
(iter3 also needed grad_ckpt — sessions-8 long seqs OOM'd plain 2/8 at step 777.)

## ★ VERDICT (3 iterations): iter1 = BEST (88.8%), beats champion v1.0.0 (68.5%) by +20.3% on the
current contract. iter2 (in_stock top-up) and iter3 (scale-up) both regressed via whack-a-mole.
iter1 GGUF: artifacts/gguf/iter1/lfm2.5-230m-iter1-Q8_0.gguf. RECOMMEND promoting iter1 to the shipped
slot (handles facets+forms + aliased schemas the champion cannot). Ship decision left to user.

## Iteration 4 — clean volume test (scale 4 + sessions 6 + _cal, 42.3M tok) — REJECTED — 2026-07-12 13:03:07 CEST
Hypothesis: iter3's rag gain came from volume, its boundary loss from sessions-8 → iter4 = iter1's mix
DOUBLED at sessions 6. **RESULT: iter4 86.8% < iter1 88.8% — WORST of all 4.** Hypothesis FALSIFIED:
rag_faithful DROPPED to 62% (iter1 71, iter3 88) — the iter3 rag gain was NOT volume-driven. comparison
12%, refusal 74%, tool_sel 90% all down. Note: iter4 eval_loss 0.046 < iter1 0.053 yet task score LOWER
— **eval_loss decoupled from task metrics** (more next-token fit ≠ better agent behavior). (iter4 train
killed at step 1494, resumed from checkpoint via new --resume flag.)

## ★★★ FINAL VERDICT (4 iterations, 2026-07-12 13:03:07 CEST) — iter1 is the OPTIMUM (88.8%).
iter2 87.4%, iter3 87.3%, iter4 86.8% — every data change (top-up / scale+sessions8 / clean-volume)
REGRESSED. iter1's specific mix (scale 2 / 18.8M tok / sessions 6 / +_cal flash core) is a defended
sweet spot. Beating it needs careful multi-dim balancing or a non-data lever (LR/schedule/base), not
more/different data — STOPPED iterating. **DELIVERABLE: iter1, beats shipped champion v1.0.0 (68.5%) by
+20.3% on the current facet+form contract.** GGUF: artifacts/gguf/iter1/lfm2.5-230m-iter1-Q8_0.gguf.
RECOMMEND promoting iter1 to the shipped slot (ship decision left to user).

## Non-data levers (push toward 100%) — 2026-07-12 15:16:33 CEST
Data changes exhausted (iter1 optimum). Tried TRAINING/weight-space levers on iter1's data:
- **completion_only_loss=ON (`col`) = 89.4% — NEW BEST (+0.6 vs iter1 88.8).** Assistant-only loss lifted
  rag_faithful 71→83% (+12, the "retrieval-capped" dim MOVED), comparison 38→44, form 90→100, refusal
  83→85; only total_correct fell 60→50. Champion never used this — clear canon win.
- model soup iter1+iter3 = 88.2%, iter1+iter3+iter4 = 88.2% — below iter1 (averaged to mean). Not the way.
**NEW LEADER: col (89.4%).** GGUF artifacts/gguf/col/. Next: test completion_only on larger data (iter3col).

## fl — all-flash proportional data + completion_only_loss — NEW BEST 91.3% — 2026-07-12 18:00:00 CEST
data/dataset_fl (flash+flash-lite pool teacher, deepseek judge, scale 3 sessions 6, 14.7k ex / 20.9M tok)
+ completion_only_loss 1.3ep + the rag_answer-verifier fix. **91.3% (873/956) — beats col 89.4%, iter1
88.8%.** FIRST data change that HELPED (all-flash quality + PROPORTIONAL recipe mix, not a skewed top-up):
comparison 44→75 (+31!), rag_faithful 83→92, listing 75→88, no_unsolicited_add 85→100, cart_preserved
75→85, total_correct 50→55; minor loss compound 55→50, refusal 85→79. +22.8 over shipped champion (68.5).
Validates scaling all-flash proportional data → champion-scale run justified. GGUF artifacts/gguf/fl/.
