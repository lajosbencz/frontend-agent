# @lajosbencz/frontend-agent

Drive the **LFM2.5-230M frontend-agent** model in the browser - a tiny, on-device web agent that
calls real tools and answers grounded in retrieved context. Fully typed, framework-agnostic, loads
the GGUF from Hugging Face via [wllama](https://github.com/ngxson/wllama) (no server-side inference).

The model is trained for **patterns, not facts**: you supply the tools and the grounding context at
runtime, and the library reproduces the exact v1.0.0 model contract (system prompt, tool-call format,
tool-result shapes, and a GBNF grammar that pins tool ids to real search results at decode time).

## Install

```bash
npm i @lajosbencz/frontend-agent @wllama/wllama
npm i minisearch stemmer            # optional: the in-browser RAG adapter (./rag)
```

## Quickstart

```ts
import { createAgent, buildRegistry, WllamaEngine, buildSystemPrompt } from '@lajosbencz/frontend-agent'
import { referenceTools } from '@lajosbencz/frontend-agent/reference'
import { LocalMiniSearchRAG } from '@lajosbencz/frontend-agent/rag'

const rag = new LocalMiniSearchRAG({ catalog, knowledge })      // your indexed data
const tools = referenceTools({
  rag,
  cart: myCartHandlers,        // add/remove/view/clear over your own state
  navigate: (target, id) => router.push(pathFor(target, id)),
})
const registry = buildRegistry(tools)        // schemas + handlers, what createAgent expects

const engine = new WllamaEngine({
  // loads https://huggingface.co/lazos/lfm2.5-230m-frontend-agent/resolve/main/...-v1.0.0-Q6_K.gguf
  model: { repo: 'lazos/lfm2.5-230m-frontend-agent', version: 'v1.0.0', quant: 'Q6_K' },
  wllamaAssets,                // wllama single/multi-thread WASM URLs
  onProgress: (p) => {},
})

const session = createAgent({
  engine,
  tools: registry,
  systemPrompt: () => buildSystemPrompt({ persona, catalogHint: () => rag.hint(6), toolSchemas: registry.schemas }),
})

session.on((e) => {
  if (e.type === 'assistant') console.log(e.text)
})

// one entry point - feed it from a text box, an API, or a speech-to-text transcript:
await session.submit('do you have any espresso grinders?')
session.abort()               // cancel an in-flight turn
```

`submit(text)` is the whole input channel - the library is agnostic to where the text comes from.
Wire your own source (typed box, an external API, or a speech-to-text engine like Whisper) and call
`submit` with the resulting text. The demo shows a Whisper → `submit` voice path.

## Model source

`WllamaEngine`'s `model` resolves a Hugging Face GGUF by default:
`https://huggingface.co/{repo}/resolve/main/{repo-basename}-{version}-{quant}.gguf`. Override any of
`{ repo, version, quant }`, or pass `modelUrl` to self-host. Cross-origin loading under COOP/COEP
requires the page to be cross-origin-isolated; the HF `resolve` CDN sends permissive CORS.

## Cross-origin isolation (multi-threading)

wllama runs **multi-threaded** when the page is cross-origin isolated (`SharedArrayBuffer`), and
**falls back to single-thread** otherwise - slower, but works with no action required. To enable
threads, make the page cross-origin isolated by either:

- serving it with `Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Embedder-Policy:
  require-corp` (or `credentialless`) headers, or
- on a static host that can't set headers (e.g. GitHub Pages), registering a COI service worker such
  as [`coi-serviceworker`](https://github.com/gzuidhof/coi-serviceworker) - the demo does this.

The library deliberately **does not register a service worker** - an SW hijacks your whole origin's
fetches and is a deployment concern you own. Note: under COEP `require-corp`, the cross-origin HF
model load needs the response to send CORP or be fetched CORS/credentialless; `coi-serviceworker`'s
**credentialless** mode handles this (so threads + the HF default compose on Pages).

## Exports

- `.` - core: `createAgent`, `buildRegistry`, `WllamaEngine`, `StubEngine`, `buildSystemPrompt`,
  `parseToolCalls`, `renderToolCalls`, `buildToolGrammar`, and all types.
- `./reference` - `referenceTools({ rag, cart, navigate })`: the 7 canonical tools
  (search_catalog, search_knowledge, add/remove/view/clear cart, navigate) with trained result shapes.
- `./rag` - `LocalMiniSearchRAG` (in-browser BM25) + `createRagClient` (bring-your-own `POST /search`).

Input is source-agnostic: `session.submit(text)` is the only feed point - connect a text box, an API,
or a speech-to-text transcript. (The library ships no STT/TTS; the demo shows a Whisper voice path.)

## License

Apache-2.0. The model weights it drives are under the LFM Open License v1.0 (see the model repo).
