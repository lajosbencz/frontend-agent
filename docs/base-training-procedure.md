# Architecture: a generic edge web-agent (LFM2.5-230M)

**Shipped as v1.0.0** (the champion, 95.2% held-out eval). One small on-device model drives **any**
modern ecommerce site's assistant — RAG chat grounded in the site's knowledge base, plus tool use
against the site's actions — configured at **inference time** by injecting that site's KB and tool
list, with **no domain facts baked into the weights**. Train once, ship the same GGUF to every site;
each site supplies a config bundle.

The single-domain BrewCraft origin is gone: generation iterates over ~25 data-driven domain packs,
answers are open-book RAG grounded in retrieval results, and tool lists vary per example. This doc
states the thesis, the system as built, and the pipeline that produces it.

## 1. Core thesis: train skills, not facts

The model should learn **behaviors that read their inputs**, never a vocabulary:

- **Grounded answering** — answer from KB passages present *in the context*, and say "not covered"
  when they aren't. (Not: recall espresso trivia from weights.)
- **Tool selection & argument binding** — pick the right tool from the tool list *in the context*
  and fill args with ids/slugs *from the catalog in the context*. (Not: memorize `add_to_cart`.)
- **Conversation & reference tracking** — coreference, ordinals, "add them all", topic switches,
  multi-turn sessions — all domain-independent.

If a behavior only works because the model saw espresso data, it won't transfer. The test for every
training example: *would this still be correct if you swapped in a mattress store's KB and tools?*

## 2. The generalization seams (what carries the thesis)

The generalization seams separate config from weights, so the same GGUF works on any site:

| Mechanism | Where | Why it generalizes |
|---|---|---|
| **Catalog-in-context** | `prompt/catalogContext.ts`, injected system prompt | Slugs come from the prompt, not weights. The model learns to *read* a product list. |
| **Tool-schema-in-prompt** | `config/tool_schema.json` → system prompt | Tools are described in-context; the model learns the call format, not a fixed toolset. |
| **Compositional generation** | `kbft/generic_gen.py` | Correctness (tool calls, ids, results) is deterministic; the teacher only writes surface text. Domain-independent by construction. |
| **Data-driven domain packs** | `data/packs/*.json` → `kbft/adapters/pack.py` (`PackAdapter`) | All domain specifics are pure data. No per-domain Python. The generator iterates N packs; the runtime loads one. |
| **Anti-forgetting mix** | `general_instruct_frac` | Keeps base direct-answer ability. |

## 3. What was changed to kill the single-domain lock

Three things once baked espresso into the weights; each is now generic:

1. **Open-book RAG QA.** Answers ground in retrieved KB passages injected as `search_knowledge` tool
   results, not recalled from memory — and refuse when the passage set doesn't contain the answer.
   The old closed-book `domain_qa`/`procedural_howto`/`policy_qa`/`kb_direct` recipes are gone.

2. **Many synthetic domains.** Generation runs across ~25 verticals (`data/packs/*.json`), so no
   single vocabulary dominates and the model can't overfit to one catalog's surface regularities.

3. **Varied tool lists.** Tool names, arg keys, and schemas are randomized per example
   (`kbft/tools.py`, `alias_tools`), so reading the injected schema is the only reliable strategy.

## 4. The system-prompt contract (the runtime interface)

Freeze a **structural template** with labeled slots. Every site fills the same slots; the model
learns the structure, so any config works:

```
<persona>            # 1–2 lines: who the assistant is for this site
<catalog>            # a SHORT list of headline entities the tools act on (id/slug + label) — a hint,
                     #   not the full catalog; the model searches for the rest via the tool
<tools>              # JSON tool schemas available on this site (incl. search_catalog/search_knowledge)
<rules>              # invariant behavior: ground answers in tool results, only act on request, refuse cleanly
```

KB passages are **not** in the system prompt — they arrive as **tool results** when the model calls
`search_knowledge` (§7). The two grounding sources: **search results** (prose passages → answers)
and **`<catalog>`** (actionable entities → tool args). Training must exercise both and their
interaction (search → informed tool call), which is the whole point of the product. Keep `<catalog>`
a bounded hint even on large sites — the search tool, not the prompt, is how the model reaches the
long tail.

The template is the contract between training and every deployment. Version it; both the data
generator and the runtime import it from one source.

## 5. Generalized recipe taxonomy

The recipes live in `kbft/generic_gen.py` as **~6 domain-independent skill families**, each a
pack-parameterized function — the recipe logic is identical across verticals; only the injected
KB/catalog/tools change.

| Family | From today's recipes | What it teaches |
|---|---|---|
| **RAG-answer** | domain_qa, procedural_howto, policy_qa, kb_direct, comparison | Call `search_knowledge`, answer strictly from the returned results; stay grounded; **refuse when absent**. |
| **Tool-act** | entity_action, buy_now, cart_view/remove, clear_cart, navigate | Select tool from schema, bind args from catalog. |
| **Retrieve-then-act** | recommendation, bundle, constrained_reco, combo_check, compatibility | KB/attribute reasoning → informed tool call. |
| **Reference & session** | ref_add, ref_ordinal, set_ref_add, entity_switch, multi_turn_session | Coreference, ordinals, topic switching, multi-turn. |
| **Extract** | extract_order, guided_checkout | Pull structured fields from NL into tool args. |
| **Refuse & recover** | robustness, unknown_product, oos_*, out_of_scope, error_recovery, counterfactual | Honest not-found, out-of-scope decline, tool-error recovery. |

The **refusal/counterfactual** family is more important here than in single-domain: a config-driven
model must reliably say "this site doesn't sell/cover that" for arbitrary KBs, and must not invent
ids absent from the injected catalog.

## 6. Domain pack: the portable config contract

A site is onboarded by supplying a pack — pure data (`data/packs/*.json`), loaded via
`kbft/adapters/pack.py` (`PackAdapter`). No per-domain Python. The generator iterates over
**N packs**; the runtime loads **one**.

```
domain_pack:
  persona:        str
  kb_docs:        [ {id, title, text} ]        # chunked; feeds RAG at train + inference
  catalog:        [ {id, label, attrs{...}, group} ]
  tools:          [ json-schema ]              # this site's actions
  relations:      [ {from, key, to} ]          # optional: compatibility/bundles
  policies:       [ doc_id ]                   # shipping/returns/FAQ
  negatives:      { unknown_entities[], oos_topics[] }   # for refusal training
```

**All pack surface text is teacher-authored — never raw dataset text.** Raw sources (Amazon meta) are
SEO/marketing soup; grounding `search_knowledge` on that teaches the model to ground on garbage. So
the same compositional rule that governs utterances governs the KB itself: **real facts in,
teacher-written surface out.** Two sources, one clean end-state:
- **Reframed packs** — sample real catalogs (Amazon-Reviews-2023) for *facts* (real titles, brands,
  categories, price scale → no hallucinated catalog), then a teacher pass rewrites each item's messy
  text into clean, consistent KB prose + blurb, **grounded strictly to the given details (forbidden
  to invent specs/numbers)**.
- **Synthetic packs** — for verticals HF lacks (crypto, movies, portfolios, SaaS, services), the
  teacher synthesizes catalog + KB from scratch. Same grounded, clean surface.

Both run through the same teacher path (reframe = rewrite-from-seed, synthesize = author-from-nothing)
and yield uniform clean packs. Randomize entity vocab, attribute names, price ranges, tool names.

The teacher is `kbft/teacher.py`. The **production teacher is `google/gemini-2.5-flash` via
OpenRouter** (`provider=openrouter`, key from `OPENROUTER_API_KEY`) — it produced the shipped v1.0.0
dataset. Local dev can point the same interface at Ollama.

Target: enough distinct packs that the model can't memorize any one. Start ~15–30 verticals; the
cross-domain eval (§9) tells you when coverage is sufficient.

## 7. RAG as a tool (not context injection)

Retrieval is **a tool the model calls**, not passages the host pre-injects. This reuses the
existing tool-calling machinery entirely (`search_docs`/`search_products` already are this), and
makes the model **backend-agnostic**: it learns "call search → read the results → answer from them"
and never learns *how* retrieval happened. Vector, BM25 fulltext, hybrid, a flat file — identical
from the weights' view. That is the generalization.

**The contract is two layers:**

- **Model-facing (frozen — the grounding contract the weights learn):** the tool's result *shape*.
  ```
  search_catalog(query, filters?)  → [{id, title, snippet, price?, attrs?, score}]
  search_knowledge(query)          → [{id, title, snippet, score}]
  ```
  The result **shape** must be identical across all domains — it's what the model learns to read.
  Tool *names* may be randomized per site (§8); the result shape may not.

- **Host-facing (configurable — bring your own DB):** the endpoint the tool handler calls.
  ```
  POST {RAG_ENDPOINT}/search   { index: "catalog"|"knowledge", query, filters, top_k }
                             → { results: [{ id, title, text, score, meta }] }
  ```
  The handler normalizes that into the model-facing shape. A site points `RAG_ENDPOINT` at their
  Qdrant/pgvector/Elastic/Typesense adapter. The demo uses a self-contained Nitro route
  (`server/api/search.post.ts`) backed by **SurrealDB** (BM25 fulltext → no embedding model, one
  binary; HNSW vector is a later upgrade behind the same contract). LLM inference stays on-device;
  only retrieval hits the service.

**Train/inference symmetry is automatic** because both ground on the same tool-result shape. No
retriever in the runtime, no context-slot to keep in sync.

### 7a. The generator's ground-truth rule (PARAMOUNT)

The compositional generator must **simulate the retrieval loop at generation time** and treat its
output as the *only* ground truth. This is non-negotiable and shapes every grounded recipe:

1. Form a user query.
2. Run a **generation-time retriever** — BM25/keyword over the pack, a stand-in for the deployment
   RAG endpoint (the demo's SurrealDB). It must behave like the real thing so training matches
   inference.
3. Its top-k output becomes the `search_*` **tool-result message** — the *only* source the answer
   may use.
4. The teacher writes the answer **grounded strictly in that result set**; it is forbidden to reach
   past it into the full KB or its own knowledge, even though the pack knows more.
5. Retrieval decides truth: gold-in-results → grounded answer; nothing relevant → **refusal**.

The same rule governs actions: a slug in `add_to_cart` must come from a `search_catalog` result,
never from memory. At runtime the model likewise sees only tool results — so training this way is
the only way the behavior transfers.

- **Gold + distractors** — retrieval naturally returns the answer-bearing result plus near-misses;
  the model must select within them, not parrot one block.
- **Not-found results** — some queries retrieve nothing relevant → refusal. The single most
  important RAG behavior, and the one small models fail without explicit training.
- **Query formulation** — the model learns to turn the user's ask into a good search `query` arg.

### 7b. Genericity rule (PARAMOUNT)

Every recipe operates on `(pack, generic intent templates)` **alone** — retrieve, ground, refuse.
**No domain-specific logic**: no per-vertical `SEARCH_SPECS`, `NEEDS`, `BUNDLES`, or compatibility
tables. If a recipe cannot run from pack data + the retriever generically, it does not belong in the
generic generator. It must yield identical-quality data for electronics, crypto, or movies without a
line that knows the topic. (The old espresso recipes are pattern references, not code to port.)

Constraint: the 230M context budget (`limits.ts`, N_CTX=8192) must hold persona + catalog + tools +
the search results + history. Budget `top_k` and snippet length against that; the existing
system-prompt-size warning already guards it.

## 8. Tool-list generalization

Per pack/pass, transform the tool schema so the model reads rather than recalls. **Implemented** in
`kbft/tools.py` (`alias_tools`), applied via `ctx.call(canonical, **kwargs)` which maps both the tool
name and the arg keys so every emitted call matches the injected schema:

- **Procedural tool names** — composed from verb×object synonym pools × naming convention
  (snake/camel/dotted/flat), unique within the set → ~100+ names/tool (465 distinct over 400 seeds).
  An effectively OPEN name space, so the model cannot memorize a fixed set — it must read the schema.
  This is what supports **arbitrary tool names** at a site.
- **Procedural argument names** — same idea on arg keys (`query`→`q`/`term`/`keywords`,
  `id`→`sku`/`product_id`, `quantity`→`qty`/`n`, `max_price`→`under`/`budget`). Schema `properties` +
  `required` are rewritten and the call emits the matching keys.
- **Subset & permute** (future) — expose a random subset in a random order; sometimes omit a tool the
  user asks for → refusal ("this site can't do that").

Keep the *call syntax* fixed (LFM2.5's `<|tool_call_start|>` format) — that's what the runtime parses.
Vary everything semantic above it. Verify true generalization with **held-out names** in eval (§10):
inject tool/arg names never seen in training and confirm correct calls.

## 9. Training procedure

| Knob | Value | Rationale |
|---|---|---|
| Base model | LFM2.5-230M (revisit 350M) | Chosen size; re-verify after multi-domain (harder task). |
| Method | full fine-tune, fp32 | Behavior shaping across domains; LoRA optional if forgetting is controlled. |
| Domain mix | round-robin over N packs, balanced | No vertical > ~1/N of data; prevents vocab dominance. |
| Skill-family balance | ~40% tool / RAG-act, ~45% RAG-answer (incl. refusals), ~15% ref/session/extract | Keep tool-vs-answer balance from Loop work; refusals meaningfully weighted. |
| Anti-forgetting | ~5% general instruct, no tools | Same as now (`general_instruct_frac`). |
| Token budget | ≥30M (50M better) | Unchanged; but spread across domains, not passes of one. |
| Epochs | ~1.3 | Unchanged; low to limit memorization. |
| Scale lever | per-pack, demo only | On real multi-domain corpora, breadth fills the budget; `scale` stays a demo crutch. |

Mechanics: incremental per-pass dump (`raw_generated.jsonl`), dedup/split, resilient teacher,
`--from-raw` recovery, and a **per-domain pass loop** around the recipe loop
(`scripts/generate_generic.py`).

## 10. Evaluation: held-out domain (the real metric)

Single-domain eval can't detect memorization. The generalization metric is **train on N−1 verticals,
eval on a fully unseen one**:

- Build an eval pack for a vertical **not** in training. Inject its KB + tools.
- Measure: tool-selection accuracy, arg-binding validity (ids exist in injected catalog),
  RAG-answer faithfulness (answer supported by injected passage), **refusal correctness** (not-found
  and out-of-scope), and reference tracking.
- A model that scores well on a held-out vertical has learned the skills, not the facts. That is the
  go/no-go for the "drop domain knowledge" thesis.

`scripts/eval_generic.py` loads an arbitrary eval pack and asserts against its injected config.
Held-out packs are pinned in `kbft/holdout.py` (`EVAL_HOLDOUT` = videogames + brewcraft); the
leakage gate in `scripts/snapshot_dataset.py` fails the snapshot if any held-out id reaches training.

## 11. Deployment: one model, per-site config bundle

Ship the single GGUF to every site. Each site provides a **config bundle**:

```
site-config/
  system-template   # the §4 slots filled with this site's persona + rules
  tools.json        # this site's tool schemas (incl. search_*) → registry.ts
  catalog.json      # the bounded headline entities for the <catalog> hint
  RAG_ENDPOINT      # URL of the site's /search service (their DB behind the §7 contract)
```

The in-browser runtime (`wllamaClient` + `useAgentLoop`) already assembles system prompt + tools +
history and dispatches tool calls; retrieval is just another tool whose handler POSTs to
`RAG_ENDPOINT`. No retriever baked into the model, no per-site training, no per-site GGUF —
onboarding a site is authoring a bundle and standing up a `/search` endpoint (the demo's SurrealDB
Nitro route is the reference implementation).

## 12. Pipeline (end to end)

1. **Build packs** — `scripts/build_packs.py`; real catalogs via `scripts/sample_amazon.py`
   (Amazon-Reviews-2023 → facts), exotic verticals via `scripts/synth_packs.py` (teacher-authored).
   Output: `data/packs/*.json`.
2. **Generate SFT** — `scripts/generate_generic.py`: compositional, RAG-grounded generation over all
   packs (`kbft/generic_gen.py`), tool names aliased per pass (`kbft/tools.py`).
3. **Snapshot** — `scripts/snapshot_dataset.py`: version the dataset, record the manifest, run the
   `kbft/holdout.py` leakage gate.
4. **Train** — `scripts/train.py`: full fp32 fine-tune of LFM2.5-230M.
5. **Eval** — `scripts/eval_generic.py` + `scripts/report.py`: held-out-domain eval (videogames +
   brewcraft), regression-gated against the same-size champion.
6. **Export** — `scripts/export_gguf.py`: GGUF quants for the in-browser runtime.

The demo site (brewcraft/espresso) is held **out** of training and handled zero-shot at inference
through the RAG/tool contract — the demo directly proves the thesis, and no vertical is elevated.

## 13. Known limits / risks

- **Small-model RAG faithfulness.** 230M grounds and refuses reliably in eval; `rag_faithfulness`
  sits ~17/28, partly an eval ceiling (BM25 returns the wrong doc) rather than hallucination. Further
  gains need a retrieval fix or a paid regen, not more student training (see §15).
- **Tool-name randomization vs consistency.** Too much variety may hurt convergence; too little
  re-bakes a fixed toolset. Sweep the alias rate.
- **Context budget.** k passages + catalog + tools + history against 8192 for 230M. May force small
  k or aggressive chunking; measure token pressure per vertical.
- **Retriever quality is now in the loop.** A bad retriever starves grounding; the model can't fix
  missing passages. Retriever eval becomes part of site onboarding.
- **Real-pack sourcing cost.** Diverse verticals need catalogs/KBs. Synthetic packs help but must be
  realistic enough to transfer.

## 14. Versioning (semver, `vMAJOR.MINOR.PATCH`)

- **v1.0.0 is the first stable release** — the v0.9.6 generation (95.2%) promoted to ship. MAJOR
  bumped from 0 on that ship.
- **MINOR** = a synthetic-dataset *generation* (a full regen via the cloud teacher). A new/changed
  recipe set that regenerates the dataset bumps MINOR.
- **PATCH** = a *training increment* on an existing dataset (hyperparams, resume, re-quant).
- Within a version we train multiple **sizes** (230M/350M) and export multiple **quants**; those are
  filename fields (`lfm2.5-{size}-v{version}-{quant}.gguf`), not version bumps.
- Backfill: the pre-semver runs map `v6→v0.6.0`, `v6.1→v0.6.1`.

## 15. Iteration learnings (v0.6 → v0.7)

The thesis (§1) held, but a *generalist* small model still needs behaviours hardened by adversarial
probing on the held-out demo. Each was turned into a generic recipe/rule (never a domain hack):

- **Safety is trainable and worth it.** Payment/PII refusal (never echo a card), prompt-injection
  resistance, and "go to checkout → navigate, not clear_cart" were near-zero pre-v6 and maxed after.
  A small model with a *toolset gap* grabs the nearest tool, including destructive ones — give it the
  right tool (`navigate`) AND train the refusal.
- **The decisiveness pendulum.** Over-weighting clarify/capability recipes made it ask permission
  ("would you like me to?"); rebalancing toward direct-action recipes + an anti-hedge clause in the
  teacher answer-prompts restored it. Balance, not just presence, of recipes matters.
- **IDs are opaque atoms.** The model truncated `flux-machine`→`flux` (the query word). Fix: train on
  BOTH opaque (ASIN) and hyphenated-slug ids so it copies the full id verbatim from results.
- **Grounding needs the text.** How-to answers failed because the result *snippet* (160 chars) cut
  off the steps. Long knowledge snippets (480) put the answer in the passage; refusal-with-doc-present
  is then heavily penalised.
- **Reason over results, don't re-search.** Anaphora ("the second/cheapest one"), constraints
  ("under $X, in stock"), and negation ("not the expensive one") must resolve against the *last*
  results; remove targets the actual cart id and never adds on a remove.
- **Eval must model the failure, not the happy path.** The automated eval flattered the model (94%)
  until hard scenarios (unsolicited-add, cart_preserved, boundary, id-grounding) were added; only then
  did it correlate with the live experience. Build the metric from real breakage.
- **350M &gt; 230M for multi-step** (compound intent, tool routing) at a modest download cost; quant
  Q4_K_M held fidelity (often ≥ Q8) — the browser payload lever is real.
- **compound↔rag is a Pareto tradeoff** (~linear in the `kb_decisive` recipe count); teacher quality
  is the orthogonal lever that lifts everything else. `rag_faithfulness ~17/28` is partly an eval
  ceiling — BM25 retrieval returns the wrong doc — not a model failure.

## 16. Multilingual packs (locale layer)

A pack declares `"lang"` (default `"en"`); the `kbft/locales/` package (one file per language:
`en.py`, `hu.py`, …) maps it to a `Locale` that supplies the persona, a teacher output-language
directive (appended to `GEN_SYS`), the currency formatter, the deterministic user/assistant strings,
and the store-policy KB (`Locale.policy_docs`). Only the human-facing NL is localized — **the tool
contract (tool names, argument keys, result JSON shape) stays English**, mirroring deployment: an
English-scaffolded agent grounding in injected foreign-language KB. This is the generalist thesis
applied to language. Add a language = add a file + register it in `locales/__init__.py`.

**One model = one language — no mixing.** A training run is monolingual. Enforced at the source:
`generate_generic.py --lang <l>` selects ONLY packs whose `lang` matches (default `en`);
`snapshot_dataset.py --lang <l>` archives only that language's packs and
records `lang` in the manifest. The version counter (`v0.MINOR.PATCH`) stays language-neutral — each
generation gets the next MINOR regardless of language, and different languages therefore get different
version numbers (no artifact collision); the manifest's `lang` field says which language a version is.
Held-out evaluation must use a same-language held-out pack.

- **`en` is canonical and byte-identical.** The `en` locale reproduces the prior literals verbatim, and
  `pick()` draws exactly one `rng.choice` like the old inline code, so the random stream — and every
  English pack's data — is unchanged. Verify any locale change against that invariant.
- **Fold accents in ids, keep them in queries.** `_slug_id` ASCII-folds (`Jármű`→`jarmu`) so semantic
  ids stay clean atoms; `_query_from` uses Unicode `\w+` so emitted search queries keep whole accented
  words (`vonalkódolvasó`). Both are no-ops for ASCII English.
- **Locale layer kept as an example, HU track dropped.** `kbft/locales/hu.py` remains as a minimal
  example stub (distinct currency/persona, EN fallback for untranslated keys) demonstrating how to add
  a language. A fuller Hungarian track (v0.8.0 — a "bonic" workshop-management vertical, Ft currency,
  trained on its own via `--lang hu`) was explored, came out a bust, and was dropped; only the locale
  architecture and the stub remain.
