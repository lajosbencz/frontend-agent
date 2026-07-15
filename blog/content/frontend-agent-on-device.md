---
title: "Running an LLM agent entirely in your browser"
description: "A tiny LFM2.5 fine-tune that drives a storefront entirely in-browser with tool calls and RAG - trained on interaction patterns, not domain facts"
date: 2026-07-15
slug: frontend-agent-on-device
tags: [ai, localllm, webdev, machinelearning]
published: false
canonical_url: https://lajosbencz.github.io/frontend-agent/blog/frontend-agent-on-device/
draft: false
ogImage: /assets/frontend-agent-vendor.png
cover_image: https://lajosbencz.github.io/frontend-agent/blog/assets/frontend-agent-vendor.png
---

**TL;DR**: I fine-tuned LiquidAI's LFM2.5 (230M and 350M) into a generic front-end agent that runs *entirely in the browser* - no server, no API key, no cloud costs.
It doesn't just chat; it calls real tools to browse a catalog, answers grounded questions, and manages a cart.
The trick: it's trained on interaction *patterns*, not domain facts, so the same weights drive a coffee store, an absurdist emporium, or a corner grocer - with zero retraining.

[Live demo](https://lajosbencz.github.io/frontend-agent/) on Github pages.

---

## Why?

Most "AI assistant" features are a text box wired to a frontier model in someone's data center.
That's fine, but it means a network round-trip per turn, a bill per token, and your users' inputs leaving the device.

I wanted the opposite: an agent small enough to ship *with the page*.
Load it once, run it on the user's own hardware (WebGPU if available, CPU/WASM otherwise via [wllama](https://github.com/ngxson/wllama)), and let it actually *do things* in the UI instead of just describing them.

The bet was that a small model can't hold a useful amount of world knowledge, but it *can* learn a compact set of behaviors well enough to be useful.

## Patterns, not knowledge

The model does **not** know what a "BrewCraft Pico" is, or that it costs $699.

It knows how to:

- pick the right tool for an intent
- bind arguments and item ids correctly
- resolve references ("the second one", "a dozen of those")
- ground an answer in retrieved text, and *refuse* when the text doesn't contain the answer
- steer back politely when asked something off-topic

Everything domain-specific is injected **at runtime**.
Each turn, the host app hands the model a compact context: the items currently on screen (with ids and prices), the cart, and any retrieved knowledge.
The model grounds strictly in that. Swap the store, swap the injected context - the same weights work.

That's why the demo ships three storefronts on one model.
And critically, they were **held out of training entirely**.
If the model can run a store it never saw, the generalization works.

## How it actually works

Three design choices carry most of the weight.

**A frozen tool roster.**
Early on I tried teaching the model to read *arbitrary* tool schemas - variable tool names and arguments per training example so it wouldn't memorize a fixed set.
For a 230M model, that was too much to ask; it garbled calls.
So the roster is now **fixed**: eight tools with stable names (`list_items`, `get_item`, `search_knowledge`, `add_to_cart`, `remove_from_cart`, `clear_cart`, `checkout`, `navigate`) that the model learns by name.
A small, memorizable action space.
The one place variety survives is the *filter set* on `list_items`, which the model reads from the injected schema.

**RAG as a tool, not a pipeline.**
Retrieval is just `list_items` (catalog) and `search_knowledge` (guides, policies).
The model decides when to call them and grounds its reply in the results.
The backend is swappable - BM25, vector, hybrid - because only the *result shape* is the contract.
The demo uses in-browser BM25; nothing leaves the machine.

**Grammar-constrained decoding.**
Tool calls are decoded against a GBNF grammar, so every call is syntactically valid and - the important part - every id the model emits is one that actually exists in the injected context.
It literally cannot hallucinate a product id.
That single constraint removes a whole class of failures that would otherwise sink a model this small.

## Training it

The pipeline is synthetic-data distillation:

1. Defined ~18 interaction *recipes* (add-to-cart, browse, compare, price lookup, knowledge Q&A, refusal, off-scope steering, small talk, ...).
  Each recipe generates short, bounded exchanges with an example runtime context attached.
2. A teacher model writes the natural-language parts (the customer's phrasing, the grounded reply); the *structure* is deterministic and generated in code, so the tool calls and ids are always correct.
3. Fine-tune the base model on ~30M tokens of this.
  Full fine-tune, fits on a single 16GB GPU.
4. Evaluate on verticals the model never saw - plus a demo-faithful "does it survive the real UI" harness.

One deliberate choice worth flagging for anyone doing the same: **train on the *pattern*, not a blocklist.**
For "handle an off-topic request," it's tempting to enumerate a fixed list of off-topics.
Don't - the model just memorizes those strings.
Instead, generate a genuinely different off-topic examples every time (thousands of distinct ones) so it learns the *behavior* of steering, not fifteen banned phrases.

Some LLM providers might cache requests; this would duplicate training data, where we expect variety. To avoid this, seed each request appropriately.

The quality of the teaching model is of course extremely important; I limited to only Apache 2.0 licensed ones, and the best bang for buck I found at the time of writing was [Qwen3 30B through Openrouter.ai](https://openrouter.ai/qwen/qwen3-30b-a3b-instruct-2507).

## So... does it work?

> Well, yes, but actually no.

**What works:**
Structured tool calls are reliable. Add an item by name or by position, ask a price, get a grounded answer, check out - the core loop holds up, including on domains it never trained on.
For a 150 MB model running on your laptop with no server, that still feels a lot like magic.

**What doesn't (yet):**
230M parameters spread across many domains is *thin*.
During training, generalized use-cases compete for the same limited capacity.
Multi-turn fidelity is the weakest spot - over a long conversation it can drift toward the shape it was trained on rather than the specific thing you just said.
Because of this, the training regime limits to only 2 turns of conversation patterns, so does the JS runtime with a sliding window; the agent never sees more than 2 turns of conversations.
The 350M variant buys real headroom at ~1.5x the footprint, and you can switch between them in the demo to feel the difference.

I think this is an interesting frontier: instead of "can a giant model do this" (obviously), we ask *how small can you go* and still be genuinely useful on-device.

## Why on-device at all

Beyond the cool factor:

- **Privacy** - inputs never leave the device. For a lot of use-cases that's not a nice-to-have, it's the requirement.
- **Offline** - it keeps working with no connection after the first load.
- **Cost** - zero inference bill; you ship weights, not a GPU fleet.
- **Accessibility** - paired with proper ARIA roles and semantic HTML, an on-device agent can make a complex UI navigable by voice or intent.
  (Speech-to-text and text-to-speech in the demo are on-device models too - nothing is sent anywhere.)

## Try it / take it apart

- **Demo:** https://lajosbencz.github.io/frontend-agent/ (three storefronts, one model, all in your tab)
- **Code:** [GitHub](https://github.com/lajosbencz/frontend-agent) - Apache-2.0 client library + the Nuxt demo
- **Models:** [230M](https://huggingface.co/lazos/lfm2.5-230m-frontend-agent) &middot;
  [350M](https://huggingface.co/lazos/lfm2.5-350m-frontend-agent) on Hugging Face
- **Dataset:** [frontend-agent-sft](https://huggingface.co/datasets/lazos/frontend-agent-sft)


---

*Built on [LiquidAI LFM2.5](https://huggingface.co/LiquidAI/LFM2.5-230M).
Model weights inherit the LFM Open License v1.0; code and this post are Apache-2.0 / CC-BY*
