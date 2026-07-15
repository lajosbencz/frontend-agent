/** Frozen model-facing result shapes (what the model was trained to read from `search_*` tools). */
export interface CatalogResult {
  id: string
  title: string
  snippet: string
  price: number | null
  in_stock: boolean
  attrs: Record<string, unknown>
  score: number
}

export interface KnowledgeResult {
  id: string
  title: string
  snippet: string
  score: number
}

/** Minimal catalog item used to resolve a cart action (add_to_cart). */
export interface CatalogItemLite {
  id: string
  title: string
  price: number | null
  in_stock: boolean
}

/** A retrieval backend behind the `search_*` tools. Any implementation works as long as it returns
 *  the frozen result shapes above. */
export interface RagBackend {
  searchCatalog(query: string, opts?: { maxPrice?: number; k?: number }): Promise<CatalogResult[]>
  searchKnowledge(query: string, k?: number): Promise<KnowledgeResult[]>
  /** A bounded `Title [id]; ...` hint for the system prompt (optional). */
  hint?(n?: number): Promise<string> | string
  /** A representative page of on-screen catalog items for the injected VIEW (optional). */
  representativeItems?(n?: number): Promise<CatalogItemLite[]> | CatalogItemLite[]
  /** Resolve a catalog item by id, for cart actions (optional). */
  getItem?(id: string): Promise<CatalogItemLite | null> | CatalogItemLite | null
}

/** Raw index rows for the in-browser MiniSearch backend. */
export interface CatalogItem {
  id: string
  title: string
  group?: string
  price: number | null
  in_stock: boolean
  summary: string
}
export interface KnowledgeItem {
  id: string
  title: string
  text: string
}
export interface RagIndex {
  catalog: CatalogItem[]
  knowledge: KnowledgeItem[]
}
