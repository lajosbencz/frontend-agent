"""BrewCraft held-out EVAL fixture — NOT a training domain.

This repo trains only generic, pack-parameterized data; it never fine-tunes a domain-specific model.
This module exists solely so the demo's own vertical (espresso equipment) can be scored as a held-out
domain the model has zero training data for. It loads the demo's real catalog + docs
(`demo/content/`) into a KB; `eval_generic.py` runs the generic recipes over it. Eval-only.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from kbft.adapters.markdown_frontmatter import MarkdownFrontmatterAdapter

REPO = Path(__file__).resolve().parents[3]
CONTENT = REPO / "demo" / "content"


def build() -> SimpleNamespace:
    """Return the eval fixture: a KB adapter over the demo content + a label. No training config."""
    adapter = MarkdownFrontmatterAdapter(docs_dir=CONTENT / "docs", entities_dir=CONTENT / "products")
    return SimpleNamespace(adapter=adapter, vertical="espresso equipment", store_name="BrewCraft")
