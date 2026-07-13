"""Markdown + YAML-frontmatter ingestion adapter.

Reads a directory of doc markdown files and (optionally) a directory of entity markdown
files whose frontmatter fields are mapped to the normalized Entity schema via an
EntityFieldMap. This is one adapter; a JSON/DB/API adapter would implement the same
IngestionAdapter interface and produce the same KB IR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

from kbft.schema import KB, Doc, Entity


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links -> label
    text = re.sub(r"[#>*_`|]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass
class EntityFieldMap:
    """Maps frontmatter keys -> normalized Entity fields (defaults suit a shop KB)."""
    id: str = "slug"
    title: str = "title"
    group: str = "category"
    summary: str = "summary"
    price: str | None = "price"
    in_stock: str | None = "inStock"
    relations: dict[str, str] = field(default_factory=lambda: {"compatibleWith": "compatibleWith"})
    path_prefix: str = "/products"


@dataclass
class DocFieldMap:
    title: str = "title"
    description: str = "description"
    path_prefix: str = "/docs"


class MarkdownFrontmatterAdapter:
    def __init__(
        self,
        docs_dir: str | Path,
        entities_dir: str | Path | None = None,
        entity_map: EntityFieldMap | None = None,
        doc_map: DocFieldMap | None = None,
    ) -> None:
        self.docs_dir = Path(docs_dir)
        self.entities_dir = Path(entities_dir) if entities_dir else None
        self.entity_map = entity_map or EntityFieldMap()
        self.doc_map = doc_map or DocFieldMap()

    def ingest(self) -> KB:
        return KB(docs=self._read_docs(), entities=self._read_entities())

    def _read_docs(self) -> list[Doc]:
        m = self.doc_map
        docs = []
        for path in sorted(self.docs_dir.glob("*.md")):
            post = frontmatter.load(path)
            meta = post.metadata
            slug = path.stem
            docs.append(Doc(
                id=slug,
                title=meta[m.title],
                description=meta.get(m.description, ""),
                body=strip_markdown(post.content),
                path=f"{m.path_prefix}/{slug}",
            ))
        return docs

    def _read_entities(self) -> list[Entity]:
        if not self.entities_dir:
            return []
        m = self.entity_map
        entities = []
        for path in sorted(self.entities_dir.glob("*.md")):
            post = frontmatter.load(path)
            meta = post.metadata
            relations = {rel: meta.get(src, []) for rel, src in m.relations.items()}
            known = {m.id, m.title, m.group, m.summary, m.price, m.in_stock, *m.relations.values()}
            attrs = {k: v for k, v in meta.items() if k not in known}
            eid = meta[m.id]
            entities.append(Entity(
                id=eid,
                title=meta[m.title],
                group=meta[m.group],
                summary=meta.get(m.summary, ""),
                body=strip_markdown(post.content),
                price=meta.get(m.price) if m.price else None,
                in_stock=meta.get(m.in_stock, True) if m.in_stock else True,
                attrs=attrs,
                relations=relations,
                path=f"{m.path_prefix}/{eid}",
            ))
        return entities
