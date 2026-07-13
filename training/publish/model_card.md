---
license: other
license_name: lfm-open-license-1.0
license_link: https://huggingface.co/LiquidAI/LFM2.5-230M/blob/main/LICENSE
base_model: LiquidAI/LFM2.5-230M
base_model_relation: finetune
library_name: transformers
pipeline_tag: text-generation
language:
- en
tags:
- lfm2
- edge
- on-device
- tool-calling
- function-calling
- rag
- agent
- gguf
- wllama
---

# frontend-agent · LFM2.5-230M (v1.0.1)

A generic English **web/front-end agent** fine-tuned from
[`LiquidAI/LFM2.5-230M`](https://huggingface.co/LiquidAI/LFM2.5-230M) — small enough to run
**entirely in the browser** (edge / local inference via wllama, no server-side model). It calls
real tools (search, navigate, cart) and answers questions grounded in retrieved context.

**Trained for patterns, not lexical knowledge.** The weights hold *behaviors* — tool selection,
argument binding, reference tracking, RAG-grounded answering, clean refusal — not domain facts.
Grounding is supplied **at runtime**: inject a compact catalog hint and serve retrieval as a
`search_*` tool, and the model grounds strictly in what it is given. Swap the site, swap the
injected context — the same model works, no retraining.

## What's new in v1.0.1

- **Reads arbitrary injected tool sets.** Tool and argument names are aliased per request during
  training, so the model selects and binds against whatever schema a site injects — variable in
  size, order, and naming — rather than a memorized fixed toolset.
- **Grounded refusal + discipline.** An added grounded-refusal signal (decline when a search
  returns nothing relevant, never pitch a spurious hit as a match, never invent ids) also lifted
  general grounding: compound multi-item adds, search-before-add, and RAG faithfulness all improved.

## Results

Evaluated on **held-out domains** (verticals with zero training data), under a strict eval with
**variable, aliased tool sets** (2–5 distractor tools injected alongside the real ones): **~92%
core capability**, stable across seeds, with near-perfect tool-selection and argument-binding. This
eval is deliberately harder and more representative of real usage than the v1.0.0 methodology, so
the headline number is not directly comparable to v1.0.0's — the gains are concentrated in reading
arbitrary tool schemas and grounded refusal. Full matrix in the project repo.

## Files

| File | Format | Size |
|---|---|---|
| `model.safetensors` | bf16 (transformers) | 459 MB |
| `*-F16.gguf` | GGUF, unquantized (fp16) | 462 MB |
| `*-Q8_0.gguf` | GGUF (near-lossless) | 247 MB |
| `*-Q6_K.gguf` | GGUF | 191 MB |
| `*-Q4_K_M.gguf` | GGUF (recommended for browser) | 153 MB |

GGUF filenames are stable across releases; pin a version via the git ref
(`resolve/v1.0.1/…-Q8_0.gguf`) or track latest via `main`.

## Usage

Transformers:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
tok = AutoTokenizer.from_pretrained("lazos/lfm2.5-230m-frontend-agent")
model = AutoModelForCausalLM.from_pretrained("lazos/lfm2.5-230m-frontend-agent")
```

Tool calling uses LFM2.5's native format — the system prompt carries the tool list between
`<|tool_list_start|>…<|tool_list_end|>`, and the model emits pythonic calls
`<|tool_call_start|>[fn(arg="v")]<|tool_call_end|>`; feed the result back as a `tool` message. The
model grounds answers only in the tool results you provide (RAG-as-a-tool). In the browser, load a
GGUF (Q4_K_M recommended) with [wllama](https://github.com/ngxson/wllama).

## Training data

Fully **synthetic** compositional SFT: tool calls, ids, and results are deterministic; a teacher LLM
(`google/gemini-2.5-flash` / `-flash-lite`) wrote only the natural-language surface. Trained with
assistant-only (completion) loss so the model learns to generate, not to echo the injected schema.
The training set is published as
[`lazos/frontend-agent-sft`](https://huggingface.co/datasets/lazos/frontend-agent-sft). The weights
are transformative and hold no catalog data.

## License

Derivative of `LiquidAI/LFM2.5-230M` → **LFM Open License v1.0** (permissive, with a commercial-use
revenue cap; attribution to Liquid AI required). See `LICENSE` and `NOTICE`.
