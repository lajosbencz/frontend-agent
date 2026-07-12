# frontend-agent

[Demo - Github Pages](https://lajosbencz.github.io/frontend-agent/)

A generic English **web/front-end agent** built on [LiquidAI LFM2.5-230M](https://huggingface.co/LiquidAI/LFM2.5-230M), small enough to run
**entirely in the browser** (edge / local inference via [wllama](https://github.com/ngxson/wllama), no server-side model). It doesn't
just chat - it calls real tools to act on a page (search, navigate, cart operations) and answers
questions grounded in retrieved context.

**Trained for patterns, not lexical knowledge.** The weights hold *behaviors* - tool selection,
argument binding, reference tracking, RAG-grounded answering, clean refusal - not any specific
catalog or domain facts. Meaning and grounding are supplied **at runtime**: the host injects a
compact catalog hint and serves retrieval as a `search_*` tool, and the model grounds strictly in
what it is given. Swap the site, swap the injected context - the same model works, no retraining.

## Repo map

```
frontend-agent/                     npm workspaces root
├─ packages/frontend-agent/  frontend-agent - the TS client library that drives the model
└─ demo/                     Nuxt demo: three storefronts (BrewCraft/Emporium/Vendor) consuming it
```

**Client library** - [`frontend-agent`](packages/frontend-agent) is a fully-typed,
framework-agnostic TypeScript package for driving the model in any web app: `createAgent(...)` returns
a session with a single `submit(text)` feed point, tool-calling + GBNF id-grounding, a configurable
Hugging Face model source, and optional RAG adapters.

**Demo** - [`demo/`](demo) is the reference consumer: three storefronts sharing one on-device
assistant. See [`demo/README.md`](demo/README.md).

## How it works

- **RAG as a tool** - retrieval is a `search_*` tool the model calls; it grounds answers in the
  results and refuses when they don't contain the answer. Backend-agnostic (BM25, vector, hybrid).
- **Tool-list randomization at training time** - tool names and argument keys were permuted per
  training example, so the model reads the injected schema rather than memorizing a fixed toolset.
- **Held-out-domain eval** - the model was evaluated on verticals never seen in training; the demo's
  BrewCraft domain is itself held out, proving the generalization thesis end to end.

## Quickstart

```bash
npm install
npm run build -w frontend-agent
npm run dev -w demo        # http://localhost:3000
```

The assistant downloads its GGUF once from Hugging Face (cached in the browser via OPFS) on first
activation - no server-side inference.

## Licensing

- **Code & docs** - Apache-2.0 ([`LICENSE`](LICENSE)).
- **Model weights** - a derivative of `LiquidAI/LFM2.5-230M`, so they inherit the **LFM Open License
  v1.0** (permissive, with a commercial-revenue cap; attribution to LiquidAI required). Cannot be
  relicensed.

## Authoring

This repository was substantially authored with the following models, under human direction and review:
- Qwen3 Coder 30B A3B Q4_K_M (local Ollama)
- Claude Opus 4.8 (Anthropic)
