# frontend-agent

[Demo - GitHub Pages](https://lajosbencz.github.io/frontend-agent/)

A generic, English **web/front-end agent** fine-tuned from [LiquidAI LFM2.5](https://huggingface.co/LiquidAI/LFM2.5-230M) (**230M** and **350M**), small enough to run **entirely in the browser** (edge / local inference via [wllama](https://github.com/ngxson/wllama), no server-side model).
It doesn't just chat - it calls real tools to act on a page (browse, look up, navigate, manage a cart, check out) and answers questions grounded in retrieved context.

**Trained for patterns, not lexical knowledge.** The weights hold *behaviors* - tool selection, argument and id binding, positional and quantity resolution, RAG-grounded answering, graceful refusal,
and steering back when asked something off-topic - not any specific catalog or domain facts.
Meaning and grounding are supplied **at runtime**: each turn the host injects a compact context - the on-screen items (with ids and prices), the cart, and any retrieved knowledge - and the model grounds strictly in what it is given.
Swap the store, swap the injected context - the same model works, no retraining.

**Client library** - [`frontend-agent`](packages/frontend-agent) is a fully-typed, framework-agnostic package: `createFrontendAgent({ persona, view, cart, tools })` returns a `Session` with a single `submit(text)` feed point and an event stream.
It handles tool-calling with GBNF-constrained decoding (well-formed calls and id-grounding by construction), a configurable Hugging Face model source, and optional RAG adapters.

**Demo** - [`demo/`](demo) is the reference consumer: three storefronts sharing one on-device assistant.
See [`demo/README.md`](demo/README.md).

## How it works

- **Frozen tool roster** - a fixed set of eight tools (`list_items`, `get_item`, `search_knowledge`, `add_to_cart`, `remove_from_cart`, `clear_cart`, `checkout`, `navigate`) the model learns by name, so a tiny model gets a small, reliable action space.
  The only per-store variance is the filter set on `list_items`, which the model reads from the injected schema rather than memorizing.
- **RAG as a tool** - retrieval is exposed as `list_items` (catalog) and `search_knowledge` (guides, policies); the model grounds answers in the results and declines when they don't contain the answer.
  Backend-agnostic (BM25, vector, hybrid) behind a small adapter - only the result shape is the contract.
- **Grammar-guaranteed calls** - decoding is constrained to a GBNF grammar, so every tool call is well-formed and every id it emits is one actually present in the injected context - no hallucinated ids.
- **Held-out-domain eval** - the model is scored on verticals never seen in training;
  the demo's BrewCraft domain is itself held out, proving the generalization thesis end to end.

## Quickstart

```bash
npm install
npm run build -w frontend-agent
npm run dev -w demo        # http://localhost:3000
```

The assistant downloads its GGUF once from Hugging Face (cached in the browser via OPFS) on first activation - no server-side inference.

## Licensing

- **Code & docs** -  [Apache 2.0](LICENSE)
- **Model weights** - [LFM Open License v1.0](https://www.liquid.ai/lfm-license)

## Authoring

This repository was substantially authored with the following models, under human direction and review:
- Qwen3 Coder 30B A3B Q4_K_M (local Ollama)
- Claude Opus 4.8 (Anthropic)
