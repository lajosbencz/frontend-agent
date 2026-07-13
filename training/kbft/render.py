"""Generic dataset assembly: render Examples with the chat template, dump, dedup, split.

Domain-agnostic — no recipe or KB knowledge, so the assembly helpers can be imported without pulling
in the generator.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from kbft.schema import Example

RAW_FILE = "raw_generated.jsonl"


def render_example(ex: Example, tokenizer, tools: list[dict]) -> dict | None:
    messages = [{"role": "system", "content": ex.system}] + ex.turns
    # The chat template requires every message `content` to be a string (its parse_content macro
    # iterates non-string content as typed parts). A rare teacher response yields a bool/number/None
    # where a string was expected (e.g. {"q": "...", "a": true}); that reaches the template and
    # crashes the whole render ("'bool' object is not iterable"). Reject only messages whose content
    # is PRESENT but non-string — assistant tool-call turns legitimately carry no `content` key.
    if any("content" in m and not isinstance(m["content"], str) for m in messages):
        return None
    # General/anti-forgetting examples render without the domain tool list.
    use_tools = tools if getattr(ex, "render_tools", True) else None
    text = tokenizer.apply_chat_template(messages, tools=use_tools, tokenize=False,
                                         add_generation_prompt=False)
    return {"text": text}


def dump_rendered(examples: list[Example], tokenizer, tools: list[dict],
                  rendered: list[dict], raw, max_len: int) -> tuple[int, int, int]:
    """Render a batch of Examples, append kept ones to `rendered` and to the open `raw` file
    handle (crash-safe incremental dump). Returns (skipped, overflow, max_tokens_seen).

    Length guard: `max_len` comes from the training config (single source of truth). Examples over it
    are kept but COUNTED, so the driver can warn — the trainer right-truncates them, and a rising
    count is the signal to shorten sessions or raise max_len."""
    skipped = overflow = max_seen = 0
    for ex in examples:
        r = render_example(ex, tokenizer, tools)
        if r is None:
            skipped += 1
            continue
        n = len(tokenizer(r["text"], add_special_tokens=False)["input_ids"])
        max_seen = max(max_seen, n)
        if n > max_len:
            overflow += 1
        rendered.append(r)
        raw.write(json.dumps(r) + "\n")
    raw.flush()
    return skipped, overflow, max_seen


def _norm_key(text: str) -> str:
    """Normalized dedup key: case/whitespace/punctuation-insensitive. Catches teacher paraphrase
    near-twins (one-word/punctuation differences) that an exact-string dedup misses and that could
    otherwise straddle the train/eval boundary."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def dedup_split(rendered: list[dict], out: Path, rng: random.Random, eval_frac: int = 12) -> dict:
    """Dedup renders (exact AND normalized-near-dup), shuffle, and write the train/eval split.
    Deduping on the normalized key BEFORE the split guarantees no near-twin straddles train/eval."""
    seen: set[str] = set()
    deduped = []
    for r in rendered:
        k = _norm_key(r["text"])
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)
    print(f"  dedup: {len(rendered)} -> {len(deduped)} unique")
    rng.shuffle(deduped)
    n_eval = max(30, len(deduped) // eval_frac)
    with open(out / "sft_eval.jsonl", "w") as f:
        for r in deduped[:n_eval]:
            f.write(json.dumps(r) + "\n")
    with open(out / "sft_train.jsonl", "w") as f:
        for r in deduped[n_eval:]:
            f.write(json.dumps(r) + "\n")
    print(f"\nTotal: {len(deduped)} (train {len(deduped) - n_eval}, eval {n_eval})")
    return {"total": len(deduped), "train": len(deduped) - n_eval, "eval": n_eval}


def finalize_from_raw(out_dir: str | Path, seed: int = 20260706, eval_frac: int = 12) -> dict:
    """Rebuild the train/eval split from an existing raw_generated.jsonl — crash recovery / re-split
    without regenerating (a wedge/OOM mid-run no longer throws away finished work)."""
    out = Path(out_dir)
    rendered = [json.loads(line) for line in open(out / RAW_FILE)]
    print(f"Loaded {len(rendered)} rendered examples from {RAW_FILE}")
    return dedup_split(rendered, out, random.Random(seed), eval_frac)
