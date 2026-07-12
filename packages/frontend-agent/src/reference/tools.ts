import type { ToolDefinition } from '../tools/types'
import type { RagBackend } from '../rag/types'

/** Cart operations the reference cart tools drive. Implement over your own state (store, signal, ...). */
export interface CartHandlers {
  add(item: { id: string; title: string; price: number }, quantity: number): void | Promise<void>
  remove(id: string): void | Promise<void>
  view(): CartView | Promise<CartView>
  clear(): void | Promise<void>
}
export interface CartView {
  cart: { id: string; title: string; price: number; quantity: number }[]
  total: number
}

/** Move the storefront to a page. `target` is one of checkout|cart|home|product; `id` for product. */
export type NavigateHandler = (target: string, id?: string) => void | Promise<void>

export interface ReferenceToolsConfig {
  rag: RagBackend
  cart: CartHandlers
  navigate: NavigateHandler
}

/**
 * The 7 canonical tools the v1.0.0 model was trained on, wired to your handlers. Schemas (names,
 * descriptions, order) are byte-identical to training; results use the trained shapes. Retrieval is
 * RAG-as-a-tool; cart acts by `id`; navigate is read-only by construction.
 */
export function referenceTools(cfg: ReferenceToolsConfig): ToolDefinition[] {
  const { rag, cart, navigate } = cfg
  return [
    {
      schema: {
        name: 'search_catalog',
        description:
          'Full-text search the product catalog. Returns matching items with their id, title, price, ' +
          'availability (in stock or not), and a short snippet. Use it for products, prices, and ' +
          'stock/availability.',
        parameters: {
          type: 'object',
          properties: { query: { type: 'string' }, max_price: { type: 'number' } },
          required: ['query'],
        },
      },
      async handler(args) {
        const query = String(args.query ?? '')
        const maxPrice = args.max_price != null ? Number(args.max_price) : undefined
        return { results: await rag.searchCatalog(query, { maxPrice }) }
      },
    },
    {
      schema: {
        name: 'search_knowledge',
        description:
          'Full-text search the knowledge base: buying guides, how-to, care, and policies. Use it for ' +
          'how-to and policy questions - not for prices or stock (use the catalog for those).',
        parameters: {
          type: 'object',
          properties: { query: { type: 'string' } },
          required: ['query'],
        },
      },
      async handler(args) {
        return { results: await rag.searchKnowledge(String(args.query ?? '')) }
      },
    },
    {
      schema: {
        name: 'add_to_cart',
        description: 'Add a catalog item to the cart by its id.',
        parameters: {
          type: 'object',
          properties: { id: { type: 'string' }, quantity: { type: 'integer' } },
          required: ['id'],
        },
      },
      async handler(args) {
        const id = String(args.id ?? '')
        const quantity = Number(args.quantity ?? 1)
        const item = rag.getItem ? await rag.getItem(id) : { id, title: id, price: 0, in_stock: true }
        if (!item) return { error: 'not_found', id }
        if (!item.in_stock) return { error: 'out_of_stock', id }
        await cart.add({ id: item.id, title: item.title, price: item.price ?? 0 }, quantity)
        return { ok: true, added: { id: item.id, title: item.title, quantity } }
      },
    },
    {
      schema: {
        name: 'remove_from_cart',
        description: 'Remove an item from the cart by its id.',
        parameters: {
          type: 'object',
          properties: { id: { type: 'string' } },
          required: ['id'],
        },
      },
      async handler(args) {
        const id = String(args.id ?? '')
        await cart.remove(id)
        return { ok: true, removed: id }
      },
    },
    {
      schema: {
        name: 'view_cart',
        description: 'Show the current cart contents.',
        parameters: { type: 'object', properties: {} },
      },
      async handler() {
        return await cart.view()
      },
    },
    {
      schema: {
        name: 'clear_cart',
        description: 'Empty the cart.',
        parameters: { type: 'object', properties: {} },
      },
      async handler() {
        await cart.clear()
        return { ok: true, cleared: true }
      },
    },
    {
      schema: {
        name: 'navigate',
        description:
          'Navigate the storefront to a page: the cart, checkout, home, or a specific product page ' +
          "(pass its id when target is 'product').",
        parameters: {
          type: 'object',
          properties: {
            target: { type: 'string', enum: ['checkout', 'cart', 'home', 'product'] },
            id: { type: 'string' },
          },
          required: ['target'],
        },
      },
      async handler(args) {
        const target = String(args.target ?? '').toLowerCase()
        if (!['checkout', 'cart', 'home', 'product'].includes(target)) {
          return { error: 'unknown_target', target }
        }
        await navigate(target, args.id != null ? String(args.id) : undefined)
        return { ok: true, navigated: target }
      },
    },
  ]
}
