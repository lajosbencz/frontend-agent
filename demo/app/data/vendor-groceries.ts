import raw from './vendor-groceries.json'

export interface GroceryItem {
  id: string
  title: string
  price: number
  description: string
  emoji: string
  shelf: 1 | 2 | 3 | 4
}

// The Vendor's own inventory - a small neighborhood grocer, unrelated to Emporium's catalog. Kept
// as JSON (not inline here) so scripts/build-rag-index.mjs can read it without a TS loader.
export const groceries: GroceryItem[] = raw as GroceryItem[]
