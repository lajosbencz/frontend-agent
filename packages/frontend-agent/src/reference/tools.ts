import type { ToolDefinition } from '../tools/types'
import type { CatalogItemLite, CatalogResult, KnowledgeResult } from '../rag/types'

const NAV_TARGETS = ['checkout', 'cart', 'home', 'product'] as const

const str = (args: Record<string, unknown>, key: string): string => String(args[key] ?? '')
const num = (args: Record<string, unknown>, key: string, dflt: number): number =>
  Number(args[key] ?? dflt)

export interface CheckoutResult {
  ok: boolean
  receipt?: { items: { id: string; title: string; price: number; quantity: number }[]; total: number }
}

/** One declarable filter arg on `list_items` (beyond `query`) - the ONLY customizable tool params.
 *  The model was trained on a VARYING filter set, so it reads whichever you advertise. `enum`
 *  restricts decoding to those exact values. */
export interface FilterParam {
  type: 'string' | 'number' | 'integer' | 'boolean'
  enum?: (string | number)[]
}
export type FilterSchema = Record<string, FilterParam>

export type ListItemsSearch = (
  query: string,
  filters: Record<string, unknown>,
) => CatalogResult[] | Promise<CatalogResult[]>

/** `list_items` with a CUSTOM filter set. Pass a plain function instead to use the default filters. */
export interface ListItemsTool {
  /** The filters `list_items` advertises. Default: `{ max_price, in_stock }`. */
  filters?: FilterSchema
  /** Run the (filtered) search; `filters` holds the values the model provided. */
  search: ListItemsSearch
}

const DEFAULT_LIST_FILTERS: FilterSchema = {
  max_price: { type: 'number' },
  in_stock: { type: 'boolean' },
}

/** One hook per FROZEN tool, keyed by the tool's exact name; you supply only the behavior. No tools
 *  can be added or renamed - the small model is trained on this exact set. Omit `navigate` to drop it. */
export interface FrontendAgentTools {
  /** Search/browse the catalog for items BEYOND the current view. A plain function uses the default
   *  filters (`max_price`, `in_stock`); pass a {@link ListItemsTool} to advertise a custom filter set. */
  list_items: ListItemsSearch | ListItemsTool
  /** Resolve a single item by id (also used internally to ground add_to_cart). */
  get_item(id: string): CatalogItemLite | null | Promise<CatalogItemLite | null>
  /** Search the knowledge base (guides, how-to, policies). */
  search_knowledge(query: string): KnowledgeResult[] | Promise<KnowledgeResult[]>
  /** Add a resolved item to the cart. */
  add_to_cart(item: { id: string; title: string; price: number }, quantity: number): void | Promise<void>
  /** Remove an item from the cart by id. */
  remove_from_cart(id: string): void | Promise<void>
  /** Empty the cart (no charge). */
  clear_cart(): void | Promise<void>
  /** Finalize the sale and return a receipt. */
  checkout(): CheckoutResult | Promise<CheckoutResult>
  /** Move the storefront (checkout|cart|home|product). Omit if the app has no routing. */
  navigate?(target: string, id?: string): void | Promise<void>
}

/** Bind the FROZEN 8-tool roster the model was trained on (kbft/tools.py) to your hooks: names,
 *  descriptions and arg shapes are byte-identical to training. These tools reach BEYOND the injected
 *  CURRENT VIEW. Returns the tools in trained order; `navigate` only if you provide its hook. */
export function referenceTools(tools: FrontendAgentTools): ToolDefinition[] {
  const list = typeof tools.list_items === 'function'
    ? { search: tools.list_items, filters: DEFAULT_LIST_FILTERS }
    : { search: tools.list_items.search, filters: tools.list_items.filters ?? DEFAULT_LIST_FILTERS }
  const filterProps: Record<string, { type: string; enum?: (string | number)[] }> = {}
  for (const [k, v] of Object.entries(list.filters)) {
    filterProps[k] = v.enum ? { type: v.type, enum: v.enum } : { type: v.type }
  }

  const defs: ToolDefinition[] = [
    {
      schema: {
        name: 'list_items',
        description:
          'Search or browse the product catalog for items BEYOND what is already shown in the ' +
          'current view. Returns matching items with id, title, price, availability and a short ' +
          'snippet. Use the filter arguments the schema offers to narrow results (e.g. price, stock, ' +
          'category).',
        parameters: {
          type: 'object',
          properties: { query: { type: 'string' }, ...filterProps },
          required: ['query'],
        },
      },
      async handler(args) {
        const filters: Record<string, unknown> = {}
        for (const k of Object.keys(list.filters)) if (args[k] != null) filters[k] = args[k]
        return { results: await list.search(str(args, 'query'), filters) }
      },
    },
    {
      schema: {
        name: 'get_item',
        description:
          'Look up a single catalog item by its id (price, availability, details). Use it to fetch ' +
          'one specific item you already know the id of.',
        parameters: { type: 'object', properties: { id: { type: 'string' } }, required: ['id'] },
      },
      async handler(args) {
        const id = str(args, 'id')
        return (await tools.get_item(id)) ?? { error: 'not_found', id }
      },
    },
    {
      schema: {
        name: 'search_knowledge',
        description:
          'Full-text search the knowledge base (buying guides, how-to, care, policies). Use it for ' +
          'how-to and policy questions, not for prices or stock.',
        parameters: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] },
      },
      async handler(args) {
        return { results: await tools.search_knowledge(str(args, 'query')) }
      },
    },
    {
      schema: {
        name: 'add_to_cart',
        description:
          'Add a catalog item to the cart by its id. Set quantity to how many the customer asked for ' +
          '(e.g. a dozen -> 12); default 1.',
        parameters: {
          type: 'object',
          properties: { id: { type: 'string' }, quantity: { type: 'integer' } },
          required: ['id'],
        },
      },
      async handler(args) {
        const id = str(args, 'id')
        const quantity = num(args, 'quantity', 1)
        const item = await tools.get_item(id) // ground the add on a real item (title/price/stock)
        if (!item) return { error: 'not_found', id }
        if (!item.in_stock) return { error: 'out_of_stock', id }
        await tools.add_to_cart({ id: item.id, title: item.title, price: item.price ?? 0 }, quantity)
        return { ok: true, added: { id: item.id, title: item.title, quantity } }
      },
    },
    {
      schema: {
        name: 'remove_from_cart',
        description: 'Remove an item from the cart by its id.',
        parameters: { type: 'object', properties: { id: { type: 'string' } }, required: ['id'] },
      },
      async handler(args) {
        const id = str(args, 'id')
        await tools.remove_from_cart(id)
        return { ok: true, removed: id }
      },
    },
    {
      schema: {
        name: 'clear_cart',
        description: 'Empty the cart (does not charge the customer).',
        parameters: { type: 'object', properties: {} },
      },
      async handler() {
        await tools.clear_cart()
        return { ok: true, cleared: true }
      },
    },
    {
      schema: {
        name: 'checkout',
        description:
          'Finalize the sale: ring up everything in the cart, charge the customer, and produce a ' +
          'receipt. Use this when the customer is ready to buy ("that\'s all", "ring me up", "I\'ll ' +
          'take it") - not clear_cart.',
        parameters: { type: 'object', properties: {} },
      },
      async handler() {
        return await tools.checkout()
      },
    },
  ]

  if (tools.navigate) {
    const navigate = tools.navigate
    defs.push({
      schema: {
        name: 'navigate',
        description:
          'Navigate the storefront to a page: the cart, checkout, home, or a specific product page ' +
          "(pass its id when target is 'product').",
        parameters: {
          type: 'object',
          properties: {
            target: { type: 'string', enum: [...NAV_TARGETS] },
            id: { type: 'string' },
          },
          required: ['target'],
        },
      },
      async handler(args) {
        const target = str(args, 'target').toLowerCase()
        if (!(NAV_TARGETS as readonly string[]).includes(target)) {
          return { error: 'unknown_target', target }
        }
        await navigate(target, args.id != null ? String(args.id) : undefined)
        return { ok: true, navigated: target }
      },
    })
  }
  return defs
}
