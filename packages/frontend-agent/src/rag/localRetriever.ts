import MiniSearch from 'minisearch'
import { stemmer } from 'stemmer'
import type {
  CatalogItem,
  CatalogItemLite,
  CatalogResult,
  KnowledgeItem,
  KnowledgeResult,
  RagBackend,
  RagIndex,
} from './types'

/** Zero-infra in-browser retrieval: MiniSearch (BM25 + fuzzy + prefix) + Porter stemmer over a
 *  supplied index. Only the result shape is the contract, not the algorithm. */
export class LocalMiniSearchRAG implements RagBackend {
  private readonly cat: MiniSearch<CatalogItem>
  private readonly know: MiniSearch<KnowledgeItem>
  private readonly catById: Map<string, CatalogItem>
  private readonly knowById: Map<string, KnowledgeItem>

  constructor(index: RagIndex) {
    const processTerm = (t: string) => stemmer(t.toLowerCase())
    const searchOptions = { fuzzy: 0.2, prefix: true, boost: { title: 2 } }
    this.cat = new MiniSearch<CatalogItem>({
      idField: 'id',
      fields: ['title', 'group', 'summary'],
      processTerm,
      searchOptions,
    })
    this.cat.addAll(index.catalog)
    this.know = new MiniSearch<KnowledgeItem>({
      idField: 'id',
      fields: ['title', 'text'],
      processTerm,
      searchOptions,
    })
    this.know.addAll(index.knowledge)
    this.catById = new Map(index.catalog.map((c) => [c.id, c]))
    this.knowById = new Map(index.knowledge.map((d) => [d.id, d]))
  }

  static async fromUrl(url: string): Promise<LocalMiniSearchRAG> {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`failed to load RAG index: ${res.status} ${url}`)
    return new LocalMiniSearchRAG((await res.json()) as RagIndex)
  }

  /** Representative sample ACROSS groups (round-robin: one per group, repeat), so the sample spans
   *  categories rather than the first n of one. Shared by `hint` and `representativeItems`. */
  private sample(n: number): CatalogItem[] {
    const groups = new Map<string, CatalogItem[]>()
    for (const c of this.catById.values()) {
      const g = c.group ?? ''
      const bucket = groups.get(g)
      if (bucket) bucket.push(c)
      else groups.set(g, [c])
    }
    const buckets = [...groups.values()]
    const picked: CatalogItem[] = []
    const max = Math.max(0, ...buckets.map((b) => b.length))
    for (let i = 0; i < max && picked.length < n; i++) {
      for (const b of buckets) {
        if (b[i]) picked.push(b[i]!)
        if (picked.length >= n) break
      }
    }
    return picked
  }

  hint(n = 6): string {
    return this.sample(n).map((c) => `${c.title} [${c.id}]`).join('; ')
  }

  /** A representative page of on-screen catalog items for the injected VIEW - the model grounds in
   *  these and reaches the rest via `list_items`. */
  representativeItems(n = 10): CatalogItemLite[] {
    return this.sample(n).map((c) => ({ id: c.id, title: c.title, price: c.price, in_stock: c.in_stock }))
  }

  getItem(id: string): CatalogItemLite | null {
    const it = this.catById.get(id)
    return it ? { id: it.id, title: it.title, price: it.price, in_stock: it.in_stock } : null
  }

  async searchCatalog(
    query: string,
    opts: { maxPrice?: number; k?: number } = {},
  ): Promise<CatalogResult[]> {
    const k = opts.k ?? 5
    const out: CatalogResult[] = []
    for (const hit of this.cat.search(query)) {
      const item = this.catById.get(hit.id as string)
      if (!item) continue
      if (opts.maxPrice != null && (item.price == null || item.price > opts.maxPrice)) continue
      out.push({
        id: item.id,
        title: item.title,
        snippet: snippet(item.summary, 120),
        price: item.price,
        in_stock: item.in_stock,
        attrs: {},
        score: round(hit.score),
      })
      if (out.length >= k) break
    }
    return out
  }

  async searchKnowledge(query: string, k = 4): Promise<KnowledgeResult[]> {
    const out: KnowledgeResult[] = []
    for (const hit of this.know.search(query)) {
      const item = this.knowById.get(hit.id as string)
      if (!item) continue
      // long knowledge snippets (480) so how-to/procedural answers are fully present in the passage
      out.push({ id: item.id, title: item.title, snippet: snippet(item.text, 480), score: round(hit.score) })
      if (out.length >= k) break
    }
    return out
  }
}

const snippet = (t: string, cap: number): string => t.trim().slice(0, cap).trimEnd()
const round = (n: number): number => Math.round(n * 1000) / 1000
