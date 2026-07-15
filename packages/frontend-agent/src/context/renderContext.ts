// Canonical C-block renderer. MUST reproduce the Python render_context (kbft/bounded.py)
// byte-for-byte; both pinned to test/context-schema.fixtures.json.

/** Bump in lockstep with the Python side + fixtures when the format changes. */
export const CONTEXT_SCHEMA_VERSION = '1.0'

/** An item shown on screen. `price` is a PRE-FORMATTED display string (e.g. `"$5.00"`). */
export interface ViewItem {
  id: string
  title: string
  price: string
}

export interface CartItem {
  id: string
  title: string
  qty: number
}

export interface KnowledgeSnippet {
  title: string
  text: string
}

export interface ContextInput {
  /** Persona/rules line - always first. */
  persona: string
  /** Items on screen, or null/empty to omit the VIEW block. */
  view?: ViewItem[] | null
  /** Cart lines; null/undefined omits the block, `[]` renders `CART: empty`. */
  cart?: CartItem[] | null
  /** Knowledge snippets, or null/empty to omit the KNOWLEDGE block. */
  knowledge?: KnowledgeSnippet[] | null
}

/** Blocks in fixed order (persona, VIEW, CART, KNOWLEDGE), blank-line joined. VIEW is 1-indexed;
 *  a null/omitted block is dropped; `cart: []` still renders `CART: empty`. */
export function renderContext({ persona, view, cart, knowledge }: ContextInput): string {
  const parts: string[] = [persona]
  if (view && view.length) {
    parts.push(
      'CURRENT VIEW (items shown to the customer):\n' +
        view.map((it, i) => `${i + 1}. ${it.title} [${it.id}] - ${it.price}`).join('\n'),
    )
  }
  if (cart != null) {
    const body = cart.length
      ? cart.map((it) => `${it.title} [${it.id}] x${it.qty}`).join('; ')
      : 'empty'
    parts.push('CART: ' + body)
  }
  if (knowledge && knowledge.length) {
    parts.push('KNOWLEDGE:\n' + knowledge.map((d) => `- ${d.title}: ${d.text}`).join('\n'))
  }
  return parts.join('\n\n')
}
