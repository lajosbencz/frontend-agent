"""Ingestion adapter interface.

An adapter reads a source knowledge base and returns the normalized KB IR. Swap the
adapter to point the whole pipeline at a different KB / source format — the markdown
frontmatter adapter is just one implementation.
"""

from __future__ import annotations

from typing import Protocol

from kbft.schema import KB


class IngestionAdapter(Protocol):
    def ingest(self) -> KB:
        """Read the source KB and return normalized docs + entities."""
        ...
