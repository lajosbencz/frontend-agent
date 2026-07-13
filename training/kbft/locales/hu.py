"""Hungarian locale — a minimal EXAMPLE showing how to add a language.

Only the highest-frequency strings are translated here; every other key falls back to `en`
(see `Locale.t`/`pick`), and the policy KB delegates to the English fallback. A production
locale would translate the full `tmpl`/`lists` sets and supply its own `policy_docs`. The tool
contract (names, arg keys, result shape) is never localized — only human-facing NL is.
"""

from __future__ import annotations

import random

from kbft.locales.base import Locale
from kbft.locales.en import EN
from kbft.schema import Doc

_TMPL = {
    "added": "{title} hozzáadva a kosárhoz.",
    "added_qty": "{n} × {title} hozzáadva a kosárhoz.",
    "removed": "{title} eltávolítva a kosárból.",
    "cart_now_empty": "A kosarad most üres.",
    "options": "Íme néhány lehetőség: {listing}.",
    "we_carry": "A kínálatunk: {cats}. Néhány példa: {listing}. Mit keresel?",
}
_LISTS = {
    "view_cart_asks": ["Mi van a kosaramban?", "Mutasd a kosaramat.", "Mi van eddig nálam?"],
    "browse_openers": ["Mit árultok?", "Milyen termékeket kínáltok?", "Mi mindenetek van?"],
}
_PERSONA = (
    "Te a(z) {store} vásárlói asszisztense vagy, egy online {vertical} kínálatban. Használd az "
    "eszközöket a katalógus és a tudásbázis kereséséhez, valamint a kosár kezeléséhez. Minden választ "
    "KIZÁRÓLAG arra alapozz, amit az eszközök visszaadnak. A kosáreszközök hívásakor a találatokban "
    "szereplő pontos tétel-azonosítót használd.")


class HuLocale(Locale):
    def money(self, v: float) -> str:
        return f"{int(round(v))} Ft"

    def policy_docs(self, slug: str, store: str, rng: random.Random) -> list[Doc]:
        # Example stub: reuse the English policy KB. A real locale writes its own.
        return self._fallback.policy_docs(slug, store, rng)


HU = HuLocale(
    lang="hu", persona=_PERSONA,
    sys_suffix=(" Írj mindent magyarul: a vásárlói üzeneteket és az asszisztens válaszait is. A "
                "pénznem forint (Ft). Az eszköz- és mezőneveket, valamint a tétel-azonosítókat NE "
                "fordítsd le."),
    hint_label="Példa katalógustételek",
    tmpl=_TMPL, lists=_LISTS, ordinals=["első", "második"],
    vague={"egy pár": 2, "néhány": 3, "egy tucat": 12},
    messy={"néhány ": 3, "": 1},
    pack_suffix="-hu",
    _fallback=EN)
