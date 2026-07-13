"""Normalized intermediate representation for any knowledge base.

Ingestion adapters convert a source KB (markdown, JSON, an API, a DB...) into these
types. Everything downstream — context building, recipes, rendering — depends only on
this IR, never on the source format.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Doc:
    """A free-text knowledge article (drives domain QA + doc-finding transcripts)."""
    id: str
    title: str
    description: str
    body: str
    path: str = ""


@dataclass
class Entity:
    """A structured catalog item (drives context injection + tool transcripts).

    `attrs` holds arbitrary extra fields; `relations` maps a relation name to a list of
    other entity ids (e.g. compatibility). `price`/`in_stock` are first-class because they
    are near-universal in shop-style KBs, but domains may leave them None and use attrs.
    """
    id: str
    title: str
    group: str
    summary: str = ""
    body: str = ""
    price: float | None = None
    in_stock: bool = True
    attrs: dict = field(default_factory=dict)
    relations: dict[str, list[str]] = field(default_factory=dict)
    path: str = ""


@dataclass
class KB:
    docs: list[Doc] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)

    def by_id(self) -> dict[str, Entity]:
        return {e.id: e for e in self.entities}

    def entities_in(self, group: str) -> list[Entity]:
        return [e for e in self.entities if e.group == group]


@dataclass
class Example:
    """One training conversation: a system string plus the non-system turns."""
    system: str
    turns: list[dict]
    # Whether to inject the domain tool list when rendering. General/anti-forgetting examples
    # (generic persona, no domain tools) set this False so they don't carry BrewCraft's tools.
    render_tools: bool = True
