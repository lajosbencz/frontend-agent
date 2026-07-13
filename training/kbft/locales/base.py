"""Locale base class + shared helpers.

Each language is ONE file in this package (en.py, hu.py, …) exporting a `Locale` singleton. A locale
owns everything language-specific for the generic generator: the persona, the teacher output-language
directive, the currency formatter, the deterministic user/assistant strings, and the store-policy KB.
The tool contract (tool names, argument keys, result JSON shape) is NOT localized — it is the frozen
contract the model reads from the injected schema; only the human-facing NL is translated. This
mirrors deployment: an English-scaffolded agent grounding in injected foreign-language KB.

Adding a language = add a file + register it in __init__. Keys missing from a non-en locale fall back
to en (a partial translation degrades gracefully instead of crashing).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from kbft.schema import Doc


@dataclass
class Locale:
    lang: str
    persona: str          # template, {store} / {vertical}
    sys_suffix: str       # appended to GEN_SYS to force the teacher's output language ("" for en)
    hint_label: str       # system-prompt catalog-sample label
    tmpl: dict            # key -> single format string
    lists: dict           # key -> list[format string] (rng.choice targets)
    ordinals: list        # ["first", "second", ...]
    vague: dict           # vague-quantity phrase -> int (cart_smart)
    messy: dict           # filler-quantity phrase -> int (messy_query)
    pack_suffix: str = ""        # filename/slug tag for synthesized packs (en: "" bare, e.g. hu: "-hu")
    _fallback: "Locale | None" = field(default=None, repr=False)

    def money(self, v: float) -> str:
        raise NotImplementedError

    def policy_docs(self, slug: str, store: str, rng: random.Random) -> list[Doc]:
        """Store-policy KB with RANDOMIZED specifics, added to each pack's knowledge index. The model
        learns to READ the policy from the retrieved passage, never to memorize a number."""
        raise NotImplementedError

    # --- catalog synthesis (kbft.synth). Defaults are English/neutral; a language file overrides. ---
    def synth_sys_suffix(self) -> str:
        """Extra system instruction so the teacher authors the synthesized catalog in this language."""
        return ""

    def synth_prompt_line(self) -> str:
        """Extra per-batch prompt line reinforcing the output language."""
        return ""

    def synth_price(self, base_usd: float) -> float:
        """Size a synthesized price (given in the $ base) for this currency."""
        return round(base_usd, 2)

    def t(self, key: str, **kw) -> str:
        d = self.tmpl if key in self.tmpl else (self._fallback.tmpl if self._fallback else self.tmpl)
        return d[key].format(**kw)

    def pick(self, rng: random.Random, key: str, **kw) -> str:
        d = self.lists if key in self.lists else (self._fallback.lists if self._fallback else self.lists)
        return rng.choice(d[key]).format(**kw)

    def ordinal(self, idx: int) -> str:
        return self.ordinals[idx]
