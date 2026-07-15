// BrewCraft domain: espresso storefront persona, wired to its own RAG index + cart.

import { createCommerceDomain } from './shared'

const PERSONA =
  'You are the shopping assistant for BrewCraft, an online espresso equipment store. Ground every ' +
  'answer ONLY in the current view and what the tools return; never state a price or stock unless a ' +
  'result says so, and never invent an item. For items beyond the view, search the catalog; for ' +
  'how-to, care, and policies, search the knowledge base. Add to the cart only when the user asks.'

export const { getSession, resetSession } = createCommerceDomain({
  domain: 'brewcraft',
  persona: PERSONA,
  ragPath: '/rag/index.json',
  shopPath: '/brewcraft/shop',
})
