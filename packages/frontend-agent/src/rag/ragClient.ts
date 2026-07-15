import type { CatalogResult, KnowledgeResult, RagBackend } from './types'

// BYO retrieval backend, normalized to the frozen model-facing shape. Point `endpoint` at your
// adapter: POST { index: "catalog"|"knowledge", query, filters, top_k } -> { results: [...] }.
const pickSnippet = (r: RemoteRow): string => r.snippet ?? r.text ?? ''

export function createRagClient(endpoint: string, init?: RequestInit): RagBackend {
  async function remote(
    index: 'catalog' | 'knowledge',
    query: string,
    filters: Record<string, unknown>,
    topK: number,
  ): Promise<RemoteRow[]> {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
      body: JSON.stringify({ index, query, filters, top_k: topK }),
      ...init,
    })
    if (!res.ok) throw new Error(`rag endpoint ${res.status}`)
    const json = (await res.json()) as { results?: RemoteRow[] }
    return json.results ?? []
  }

  return {
    async searchCatalog(query, opts = {}): Promise<CatalogResult[]> {
      const k = opts.k ?? 5
      const filters = opts.maxPrice != null ? { max_price: opts.maxPrice } : {}
      return (await remote('catalog', query, filters, k)).map((r) => ({
        id: r.id,
        title: r.title,
        snippet: pickSnippet(r),
        price: r.price ?? r.meta?.price ?? null,
        in_stock: r.in_stock ?? r.meta?.in_stock ?? true,
        attrs: r.attrs ?? r.meta ?? {},
        score: r.score ?? 0,
      }))
    },
    async searchKnowledge(query, k = 4): Promise<KnowledgeResult[]> {
      return (await remote('knowledge', query, {}, k)).map((r) => ({
        id: r.id,
        title: r.title,
        snippet: pickSnippet(r),
        score: r.score ?? 0,
      }))
    },
  }
}

interface RemoteRow {
  id: string
  title: string
  text?: string
  snippet?: string
  price?: number | null
  in_stock?: boolean
  attrs?: Record<string, unknown>
  score?: number
  meta?: Record<string, unknown> & { price?: number | null; in_stock?: boolean }
}
