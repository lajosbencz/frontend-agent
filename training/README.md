# kbft — training pipeline

Turns a set of **domain packs** into an SFT dataset and full-fine-tunes **LFM2.5-230M** into a
generic web-agent: tool selection, argument binding, and RAG-grounded answering — all read from
context at inference time, none baked into the weights. Ships as a GGUF for in-browser (wllama)
inference. See `../docs/base-training-procedure.md` for the architecture.

## Core idea

The model learns **patterns, not facts**. At inference the host injects a compact catalog hint and
serves retrieval as a `search_*` tool; the model reads ids from results and grounds answers strictly
in them. Data is generated **compositionally**: a teacher LLM writes only the natural-language
surface (utterances, grounded replies); every tool call, id, and tool result is computed
deterministically, so training data is never wrong about ids or structure. Tool names and argument
keys are randomized per example (`kbft/tools.py`), so the only viable strategy is reading the schema.

## Modules (`kbft/`)

| Module | Responsibility |
|---|---|
| `schema.py` | Normalized IR: `Doc`, `Entity`, `KB`, `Example` |
| `adapters/pack.py` | `PackAdapter` — ingests a `data/packs/*.json` domain pack |
| `generic_gen.py` | Pack-parameterized compositional recipes (RAG-answer, tool-act, reference, refuse) |
| `teacher.py` | Teacher-LLM client (OpenRouter / Ollama), schema-forced JSON + faithfulness verify |
| `tools.py` | `alias_tools` — per-example tool-name / arg-key randomization |
| `retriever.py` | Generation-time BM25 retriever (mirrors the deployment `/search` contract) |
| `holdout.py` | `EVAL_HOLDOUT` (videogames, brewcraft) + leakage assertions |
| `render.py` | chat-template render, near-dup dedup, train/eval split |
| `locales/` | Per-language layer: `en.py` (canonical) + `hu.py` (minimal example stub). One model = one language |

## Workflow

Production teacher is **`google/gemini-2.5-flash` via OpenRouter** (`OPENROUTER_API_KEY` env); local
dev can use Ollama (`--provider ollama`, host via `OLLAMA_HOST`).

The pipeline stages are `data/seeds/` → `data/packs/` → `data/dataset/`. **Nothing under `data/` is
committed** — it's all generated. The committed inputs are the *seeds*, which live in code
(`sample_amazon.py` `CATEGORIES`, `synth_packs.py` `SPECS`); the dataset lives on Hugging Face and
versioning is git tags + that published dataset. A fresh clone runs step 0 first.

```bash
export PYTHONPATH=.

# 0. seed the raw fact packs from Amazon-Reviews-2023 (subject to the source dataset's terms)
.venv/bin/python scripts/sample_amazon.py                # -> data/seeds/ (raw)

# 1. build clean training packs (reframe seeds/ + synthesize exotic verticals)
.venv/bin/python scripts/build_packs.py                  # data/seeds/ -> data/packs/

# 2. generate the SFT dataset across all EN packs (compositional; teacher writes surface text only).
# Teacher/judge = a weighted per-member roster (default: flash+flash-lite pool + deepseek judge).
.venv/bin/python scripts/generate_generic.py --scale 7 --workers 32 --lang en --verify-grounding \
    --teacher-roster '[{"weight":1,"provider":"openrouter","model":"google/gemini-2.5-flash"},{"weight":1,"provider":"openrouter","model":"google/gemini-2.5-flash-lite"}]'  # -> data/dataset/

# 3. fine-tune — the champion recipe is a preset; CLI/ENV override any value (see Config below)
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True .venv/bin/python scripts/train.py \
    --config configs/230m-16gb-full.yaml --out artifacts/full-230m   # reads data/dataset/

# 4. held-out eval (brewcraft + videogames — zero training data in these) + report
.venv/bin/python scripts/eval_generic.py --domains brewcraft --packs data/packs/videogames.json \
    --gguf <new.gguf> <prev.gguf> --n 6 --out reports/eval.json
.venv/bin/python scripts/report.py --eval reports/eval.json --out reports/report.md

# 5. export GGUF quants for the browser
.venv/bin/python scripts/export_gguf.py --checkpoint artifacts/full-230m \
    --name lfm2.5-230m-frontend-agent --quants q8_0,q6_k,q4_k_m --keep-f16
```

To cut a release, tag git (`git tag v1.1.0`) and publish to HF (`publish_subset.py` → `publish_hf.py`).
`snapshot_dataset.py --version <tag> --out <dir>` optionally freezes a labeled dataset copy (leakage
gate + manifest + card) anywhere you point `--out` (default `data/releases/`, gitignored) — for HF prep
or your own archiving.

## Config

`train.py` is configured by one typed surface (`kbft/train_config.py`, pydantic-settings) resolved
**CLI > ENV (`TRAIN_*`) > `--config` YAML > defaults** — no hand-rolled merging. Every knob is a flag,
an env var, and a YAML key. Hardware presets in `configs/`:

| preset | GPU | recipe |
|---|---|---|
| `230m-16gb-full.yaml` | 16GB | champion: full fp32, batch 2 / accum 8, paged_adamw_32bit |
| `qlora-8gb.yaml` | 8GB | 4-bit NF4 base + LoRA, paged 8-bit optim, grad-checkpointing |
| `lora-generic.yaml` | mid | bf16 LoRA (merge the adapter before export) |

Knobs include `--method full|lora|qlora`, `--lora-r/--lora-alpha`, `--max-len`, `--optim`,
`--completion-only-loss` (assistant-only loss; off reproduces v1.0.0, on is canonical for retrains),
`--max-steps` (smoke tests). Grad-checkpointing is a **weight-neutral memory lever** — off for 230M on
16GB (~20% faster), on for tighter cards.

## Runtime

Runs in the local uv `.venv` or the CUDA image `ghcr.io/lajosbencz/lfm-train` (bundles the
torch/transformers/trl/peft/bitsandbytes stack + a static `llama-quantize`). The code is generic — the
same commands run locally or in a cloud container. Vendored `llama.cpp` for export is pinned in
`vendor/README.md`.

The image ships only the heavy ML stack; the repo's own pure-python deps (`requirements-image.txt`)
are installed into the container venv at startup by `scripts/bootstrap.sh` — the image stays lean and
we bootstrap our needs. Example (rootless podman, mounting the repo + HF cache):

```bash
podman run --rm --userns=keep-id --device nvidia.com/gpu=all \
  -e PYTHONPATH=/w/training -e HF_HUB_OFFLINE=1 -e UV_CACHE_DIR=/tmp/uv-cache \
  -v $PWD:/w -v ~/.cache/huggingface:/home/trainer/.cache/huggingface \
  -w /w/training ghcr.io/lajosbencz/lfm-train:generic \
  bash -lc "scripts/bootstrap.sh && python scripts/train.py --config configs/230m-16gb-full.yaml"
```

## Adding a domain

Write a `data/packs/<slug>.json` (persona, entities, KB docs, policies) — synthetic via
`scripts/synth_packs.py` or reframed from a real catalog via `scripts/sample_amazon.py`. No per-domain
Python: recipes read the pack generically. Add `"lang"` for a non-English pack (needs a
`kbft/locales/<lang>.py`, e.g. the `hu.py` stub); a run is monolingual (`--lang`).

## Results

Held-out eval matrix and durable learnings: `reports/METRICS.md`. Champion: **v1.0.0** (95.2%).
