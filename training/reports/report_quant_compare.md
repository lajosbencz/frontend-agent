# v6 matrix — param size × quant × eval

Held-out (zero training data in these domains) · 6 scenarios/kind/config · backend ngl=99. Best config: **230m-v1.0.0-Q6_K** (96.3%).

## Fidelity matrix

| config | size | overall | tool_selection | arg_binding | id_grounded | reference_track | rag_faithful | refusal | no_unsolicited_add | compound_both | search_before_add | total_correct | navigate | cart_preserved | boundary | listing | param_search | comparison |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **230m-v1.0.0-Q4_K_M** | 153MB | 94.2% (-2.2) | 87/88 | 229/232 | 31/36 | 11/12 | 11/16 | 74/80 | 11/12 | 8/12 | 12/12 | 12/12 | 12/12 | 11/12 | 24/28 | 12/12 | 12/12 | 8/12 |
| **230m-v1.0.0-Q6_K** | 191MB | 96.3% | 88/88 | 232/232 | 34/36 | 12/12 | 13/16 | 74/80 | 10/12 | 11/12 | 12/12 | 12/12 | 12/12 | 11/12 | 24/28 | 11/12 | 12/12 | 10/12 |
| **230m-v1.0.0-Q8_0** | 247MB | 96.2% (-0.2) | 88/88 | 232/232 | 34/36 | 12/12 | 13/16 | 74/80 | 11/12 | 9/12 | 12/12 | 12/12 | 12/12 | 11/12 | 24/28 | 11/12 | 12/12 | 10/12 |

## Recommendation

**Ship `230m-v1.0.0-Q6_K`** (191MB, 96.3%) — the smallest download within 1.5 pts of the best (230m-v1.0.0-Q6_K, 96.3%).

- `230m-v1.0.0-Q4_K_M`: 94.2% (+2.2 vs best; 153MB) — too lossy
- `230m-v1.0.0-Q6_K`: 96.3% (+0.0 vs best; 191MB) — ✓ within tol
- `230m-v1.0.0-Q8_0`: 96.2% (+0.2 vs best; 247MB) — ✓ within tol

## Regression gate

No prior-version configs in this matrix — nothing to compare against.
