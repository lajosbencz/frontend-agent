# frontend-agent demo

Nuxt demo with three storefronts sharing one in-browser AI assistant that runs the
[frontend-agent](../packages/frontend-agent) model **entirely client-side** via
[wllama](https://github.com/ngxson/wllama) (llama.cpp in WASM, no server-side inference). The
assistant answers knowledge-base questions and drives the cart/navigation through real tool calls.

- **BrewCraft** (`/brewcraft`) - a fictional espresso-gear store. A **held-out** domain - the model
  was never trained on espresso data - so this directly shows the generalization thesis:
  runtime-injected catalog + KB, zero domain facts in the weights.
- **Emporium** (`/emporium`) - the same catalog/cart tool shape over a stranger, absurdist catalog
  and its own knowledge base, forced dark theme.
- **The Vendor** (`/vendor`) - a grocer you talk to directly, no browsing UI; the same 7 trained
  tools plus one bespoke `pay` tool for finalizing a sale.

See `app/pages/about.vue` (`/about`) for the full architecture writeup.

## Run

```bash
npm install
npm run dev        # http://localhost:3000
```

The assistant downloads its GGUF once (cached in the browser via OPFS) on first activation. Requires
a cross-origin-isolated context (COOP/COEP) for multi-threaded WASM - the dev server and the
`deploy/` nginx config set these headers.

## Layout

- `content/` - BrewCraft product catalog + KB docs, Emporium news, Vendor KB (`@nuxt/content`)
- `app/lib/agent/domains/{brewcraft,emporium,vendor}.ts` - wire the
  [`@lajosbencz/frontend-agent`](../packages/frontend-agent) library to each domain (persona, tools,
  Pinia cart/navigation, local RAG index)
- `app/lib/agent/engine.ts` - the shared wllama engine singleton (one model load, all three domains)
- `app/lib/agent/speech/` - optional Whisper voice input (transcript -> `session.submit`)
- `app/composables/`, `app/stores/` - thin Vue/Pinia wrappers + UI state
- `public/rag/*.json` - the in-browser BM25 indexes per domain (built by `scripts/build-rag-index.mjs`)
- `deploy/` - nginx + compose for serving the prerendered static build behind a TLS proxy

## Model

The model is driven entirely by the `@lajosbencz/frontend-agent` library, which loads the GGUF from
Hugging Face by default (`lazos/lfm2.5-230m-frontend-agent`, v1.0.0, Q6_K) and caches it in the
browser (OPFS). To change model/version/quant or self-host, pass `model`/`modelUrl` to the
`WllamaEngine` built in `app/lib/agent/engine.ts`.
