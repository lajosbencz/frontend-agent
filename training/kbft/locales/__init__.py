"""Per-language locales for the generic generator. One file per language (en.py, hu.py, …).

Register a new language by importing its singleton and adding it to `_LOCALES`.
"""

from __future__ import annotations

from kbft.locales.base import Locale
from kbft.locales.en import EN
from kbft.locales.hu import HU

_LOCALES = {"en": EN, "hu": HU}


def get_locale(lang: str) -> Locale:
    return _LOCALES.get((lang or "en").lower(), EN)


def known_langs() -> list[str]:
    return sorted(_LOCALES)


__all__ = ["Locale", "EN", "HU", "get_locale", "known_langs"]
