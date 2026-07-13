"""Conversation-turn encoding primitives — the wire shape of a chat turn.

Neutral by design: these build the message dicts the chat template renders into LFM2.5 format.
No domain or KB assumptions — just user / assistant / tool-call / tool-result turns.
"""

from __future__ import annotations

import json


def u(text: str) -> dict:
    return {"role": "user", "content": text}


def a(text: str) -> dict:
    return {"role": "assistant", "content": text}


def call(name: str, args: dict) -> dict:
    return {"role": "assistant",
            "tool_calls": [{"type": "function", "function": {"name": name, "arguments": args}}]}


def multi_call(calls: list[tuple[str, dict]]) -> dict:
    """One assistant turn emitting several tool calls at once — the batched `[fn1(...), fn2(...)]`
    form (e.g. two parallel searches for a comparison, or adding several known ids together)."""
    return {"role": "assistant",
            "tool_calls": [{"type": "function", "function": {"name": n, "arguments": a}}
                           for n, a in calls]}


def tool_result(obj) -> dict:
    return {"role": "tool", "content": json.dumps(obj)}
