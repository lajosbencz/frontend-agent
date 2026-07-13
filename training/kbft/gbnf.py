"""Generate a GBNF grammar that constrains LFM2.5 tool-call decoding to the injected tool schema.

Division of labour: the trained model supplies the POLICY (which tool, when, which id semantically);
this grammar GUARANTEES the STRUCTURE at decode time — only valid tool names, only that tool's arg
keys in the right shape, correct value types, enum values, and (when the caller passes the ids present
in the last search result) an id argument that can ONLY be one of those. That makes id-grounding
unfaultable — the `flux` -> `flux-machine` truncation class becomes impossible to emit.

The grammar is built PER TURN from the SAME aliased schema the system prompt injects, so it stays
retriever/site-agnostic (patterns, not semantics). Apply it via the llama.cpp / wllama `grammar`
sampling parameter.

Target format (LFM2.5 pythonic, single-quoted, optional special-token wrapper):
    <|tool_call_start|>[name(key='v', key2=123)]<|tool_call_end|>
"""

from __future__ import annotations

import re

_STRVAL = "strval ::= \"'\" [^']* \"'\""      # single-quoted string, no embedded quote (llama GBNF: no '.')
_NUMVAL = r'numval ::= "-"? [0-9]+ ("." [0-9]+)?'
_BOOLVAL = r'boolval ::= "True" | "False"'


def _lit(s: str) -> str:
    """GBNF double-quoted literal matching the exact string s."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _sq(s: str) -> str:
    """GBNF literal matching the single-quoted pythonic string 'value'."""
    return _lit("'" + s + "'")


def _rn(name: str) -> str:
    """A safe GBNF rule-name fragment."""
    return re.sub(r"[^A-Za-z0-9]", "-", name)


def _value_rule(tname: str, key: str, spec: dict, valid_ids, id_keys) -> str:
    """Return the GBNF expression for one argument's value."""
    if key in id_keys and valid_ids:
        return f"{_rn(tname)}-{_rn(key)}-id"          # alternation of the real ids (defined later)
    if isinstance(spec.get("enum"), list):
        return "( " + " | ".join(_sq(str(v)) for v in spec["enum"]) + " )"
    t = spec.get("type")
    if t in ("integer", "number"):
        return "numval"
    if t == "boolean":
        return "boolval"
    return "strval"


def build_tool_grammar(tools: list[dict], valid_ids: list[str] | None = None,
                       id_keys=("id",), allow_text: bool = True) -> str:
    """GBNF constraining tool calls to `tools`. If `valid_ids` is given, any `id_keys` argument is
    constrained to exactly those ids. If `allow_text`, the model may instead emit a plain reply."""
    rules: list[str] = ['sep ::= "," " "?']
    call_alts, id_alts_needed = [], []
    for t in tools:
        fn = t.get("function", t)
        name = fn["name"]
        params = fn.get("parameters", {}) or {}
        props = params.get("properties", {}) or {}
        required = list(params.get("required", []))
        rn = _rn(name)
        req_frags, opt_frags = [], []
        for key, spec in props.items():
            val = _value_rule(name, key, spec, valid_ids, id_keys)
            if key in id_keys and valid_ids:
                id_alts_needed.append((name, key))
            frag = f"{rn}-{_rn(key)}"
            rules.append(f"{frag} ::= {_lit(key + '=')} {val}")
            (req_frags if key in required else opt_frags).append(frag)
        # required args in order, comma-joined; optionals each appended optionally (matches the model)
        seq = " sep ".join(req_frags)
        for o in opt_frags:
            seq = (seq + " " if seq else "") + f"( sep {o} )?"
        rules.append(f"{rn}-call ::= {_lit(name + '(')} {seq} {_lit(')')}".replace("  ", " "))
        call_alts.append(f"{rn}-call")
    # One or more calls, comma-joined inside the brackets (`[fn1(...), fn2(...)]`) — a single call is
    # just N=1. Lets the model batch parallel calls (e.g. two searches for a comparison) in one turn.
    rules.append("call ::= ( " + " | ".join(call_alts) + " )")
    rules.append("toolcall ::= " + _lit("[") + " call ( sep call )* " + _lit("]"))
    rules.append("wrapped ::= ( " + _lit("<|tool_call_start|>") + " )? toolcall ( "
                 + _lit("<|tool_call_end|>") + " )?")
    for name, key in id_alts_needed:
        rules.append(f"{_rn(name)}-{_rn(key)}-id ::= " + " | ".join(_sq(i) for i in valid_ids))
    if allow_text:
        # a free-text reply: first char isn't a tool-call opener, then any chars (incl. newlines)
        rules.append(r'reply ::= [^\[<] [^\x00]*')
        rules.append("root ::= wrapped | reply")
    else:
        rules.append("root ::= wrapped")
    rules += [_STRVAL, _NUMVAL, _BOOLVAL]
    return "\n".join(rules)
