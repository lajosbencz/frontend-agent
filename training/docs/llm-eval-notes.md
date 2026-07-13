# LLM Evaluation — notes (CME295 L8) + how it maps to our stack

Terse distillation of the lecture, with a column for what WE already do / should do.
Our stack = LFM2.5-230M webshop agent; eval = `scripts/eval_generic.py` (held-out domains) +
`scripts/report.py` (matrix + regression gate); grounding = compositional gen + teacher.

## 1. Output-quality eval (Ashwin)
- **Scope:** "evaluation" here = OUTPUT QUALITY (not latency/cost/uptime). Hard because output is free-form.
- **Human ratings** = ideal but slow/expensive/subjective. Subjectivity is measurable via **inter-rater
  agreement** — but raw agreement rate is misleading (two random binary raters already agree ~50%). Use
  chance-corrected metrics: **Cohen's κ** (2 raters), Fleiss' κ, Krippendorff's α. Track as a health
  metric; run "agreement sessions" to align raters.
- **Rule-based (vs reference):** METEOR (MT; P/R + word-order penalty), BLEU (precision + brevity penalty),
  ROUGE (summarization). Limits: no stylistic variation, weak human-correlation, still need references.
- **LLM-as-a-judge** (the main technique): judge LLM gets `prompt + response + criteria` → outputs
  `{rationale, score}`.
  - **Score = BINARY (pass/fail)** — easier for the judge AND for human alignment; less noise than scales.
  - **Rationale BEFORE score** — same idea as chain-of-thought; empirically better.
  - **Guarantee parseable output with structured output / constrained decoding** (a.k.a. "structured
    output" at OpenAI/Gemini/Anthropic).
  - **Types:** pointwise (single) and pairwise (A vs B — good for synthesizing preference data).
  - **Biases:** (1) **position** (swap A/B, majority-vote); (2) **verbosity** (state in guidelines / ICL
    examples / length penalty); (3) **self-enhancement** — a judge prefers ITS OWN outputs → **do not use
    the same model for generation and judging; prefer a different, bigger, strong-reasoning judge**.
  - **Best practices:** crisp guidelines · binary scale · rationale-before-score · **calibrate judge vs
    human ratings** (correlation analysis; don't over-optimize the proxy — Goodhart) · **low temp (0.1-0.2)**
    for reproducibility.
  - **Dimensions:** task perf (useful/factual/relevant) + format/alignment (tone/style/safety).
  - **Factuality (needs nuance, not binary on the whole text):** decompose text → **list of atomic facts**
    → check EACH (binary) via RAG/web-search → **aggregate with importance weights**. Score = weighted
    fraction correct.

## 2. Agent failure modes (Shervin) — the diagnostic checklist
Tool call = 3 steps: **predict (tool+args) → execute → synthesize**. Failure modes:
- **Predict:** (1) should-use-tool but PUNTS ("sorry, can't") → tool-router recall error (fix router) or
  model didn't think to call (fix SFT/prompt). (2) **Tool hallucination** (calls undefined fn) → model too
  weak (upgrade) OR bad API naming/args/docstring (**rename = the 3 knobs**) OR unclear top-level "use
  available functions" instruction. (3) Wrong tool (ambiguous) → router recall + precise, non-overlapping
  API scopes. (4) Right tool, WRONG ARGS (coords 0,0) → ensure context carries needed info; add a
  prerequisite tool; actionable error instead of dummy args.
- **Execute:** (5) tool returns error/garbage → return STRUCTURED true output, not raw errors (model blames
  itself for errors); fix the tool. (6) NO response → bad for ACTION tools (model false-confirms) → always
  return meaningful output; **empty JSON `{results:[]}` > `None`** (empty = "found nothing"; None = nothing).
- **Synthesize:** (7) right output, bad synthesis → model doesn't ground (upgrade) / **too much output
  drowns the signal** (trim to meaningful) / not presented meaningfully (use structured objects w/ attrs).
- **Method:** categorize errors, fix in GROUPS. Root causes cluster into: model reason/ground, context
  relevance, tool-router/API modeling (SFT/prompt/description), or the tool itself.

## 3. Benchmarks
Knowledge: **MMLU** (57 tasks, MCQ, tests pre-training retention; hardcoded letter extraction — avoids
judge error). Reasoning: **AIME** (math, 3-digit answer), **PIQA** (physical common-sense, 2-choice).
Coding: **SWE-bench** (real GitHub PRs w/ tests; patch → run tests). Safety: **HarmBench** (provider-policy
dependent; classifier-graded; attack "succeeds" if ATTEMPTED even if low-quality). Agents: **τ-bench**
(simulated user, airline/retail; reward = DB-state change; **pass^k = ALL k attempts succeed →
reliability/consistency**, vs pass@k = at-least-one). Contamination: hashes / block-lists / fresh tests.
**Goodhart: "when a measure becomes a target it ceases to be a good measure."** Pick on the **Pareto
frontier** (quality vs price/safety/context); ultimately try models yourself.

---

## APPLIED TO OUR STACK

Already aligned ✓
- **Structured/constrained decoding** → we have GBNF (`kbft/gbnf.py`, `demo/.../gbnf.ts`): guarantees valid
  tool calls + id-grounding at decode time. This IS the lecture's "structured output" for parseable output.
- **Hardcoded answer extraction** → `eval_generic` grades tool calls / ids / tokens deterministically
  (no judge in the loop) — the MMLU-style "avoid a judge layer of error." ✓
- **Low temp for eval** → eval runs temp 0 (deterministic, reproducible). ✓
- **LLM-as-judge, done right** → our faithfulness gate (`Teacher.verify_grounded`) is binary +
  **rationale-before-score** (lists `unsupported_claims` THEN `supported`) + structured output. Matches best
  practice. And our **factuality method == the lecture's**: decompose→list claims→judge (we do the
  list-then-judge; weighting is uniform for now). ✓
- **Agent failure modes ↔ our eval dims:** #1 punt = our `tool_selection` / the rag_faithful no-search
  hedge; #2 tool hallucination ≈ our `id_grounded` (id not in results) + `invalid_tool`; #4 wrong args =
  `arg_binding`; #6 meaningful tool output = our recipes return structured results. Our recipes' gold-present
  safety net + aliasing directly attack #2/#3.
- **Goodhart / don't over-optimize the proxy** → our fixed regression gate (per-dim, same-size champion)
  is exactly this: overall% is the proxy, per-dim gate guards the real capabilities. ✓
- **Held-out / no contamination** → fail-closed `EVAL_HOLDOUT` (videogames/brewcraft), verified. ✓

To apply (ranked)
1. **[DONE] Self-enhancement bias in the faithfulness verifier.** We had teacher=verifier=gemini-2.5-flash
   → a judge grading its own family's output. Fixed: verifier defaults to a DIFFERENT family
   (`deepseek/deepseek-v4-flash`, strong from our translation sweep) + a warn if verifier==teacher. (Bias is
   weaker for grounding than for preference, but the fix is free and correct.)
2. **pass^k reliability metric (post-v0.9.6, don't perturb its eval).** We're a CART-MUTATING agent →
   reliability matters more than average. We already run canonical+aliased variants; add a **both-must-pass
   consistency** dim for critical patterns (id_grounded, no_unsolicited_add, compound) — the τ-bench pass^k
   insight. Reserve for after v0.9.6 to keep its eval comparable.
3. **Tool-result hygiene audit (data quality).** Verify recipes follow #5/#6/#7: empty search returns
   `{results:[]}` not None; action tools always return a confirmation payload; results are trimmed/structured
   so the signal isn't drowned. Quick recipe-level check.
4. **Judge↔human calibration.** We never spot-check the verifier vs a human. When enabling `--verify-grounding`
   on a paid regen, hand-audit ~20 verdicts to confirm the proxy tracks reality before trusting it.
5. **Pairwise judging (if ever comparing model outputs with an LLM):** apply position-swap + majority vote.
