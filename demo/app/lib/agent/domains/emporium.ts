// Emporium domain: absurdist storefront persona, wired to its own RAG index + cart. The knowledge
// base is the store's News section (content/emporium-news/**) - policies, restocks, and dispatches.

import { createAgent, buildRegistry, buildSystemPrompt, type Session } from 'frontend-agent'
import { referenceTools } from 'frontend-agent/reference'
import { LocalMiniSearchRAG } from 'frontend-agent/rag'
import { useAgentStore } from '~/stores/agent'
import { useCartStore } from '~/stores/cart'
import { useNavigationStore } from '~/stores/navigation'
import { getEngine } from '../engine'
import { memoizedSession } from '../sessionCache'
import { attachSessionEvents, buildCartHandlers, buildRecovery } from './shared'

const DOMAIN = 'emporium'

const PERSONA =
  'You are the clerk at Emporium, a shop that sells wonderfully impossible and paradoxical ' +
  'goods. Use the tools to search the catalog, search the news/knowledge base, and manage the ' +
  "cart. Ground every answer ONLY in what the tools return; if a search returns nothing relevant, " +
  "say you don't have that information rather than inventing one. Never state a product's price " +
  'or whether it is in stock unless a catalog result says so; for policies, restocks, or store news, ' +
  'search the knowledge base instead. When the user asks to add or find a specific item, search ' +
  'the catalog for THAT item first and act on the matching result. Only add items to the cart when ' +
  'the user asks. Use the exact item id from search results when calling cart tools. Play along ' +
  'with the absurdity of the catalog, dryly and briefly.'

const ROUTES: Record<string, (id?: string) => string> = {
  checkout: () => '/emporium/checkout',
  cart: () => '/emporium/cart',
  home: () => '/emporium',
  product: (id) => (id ? `/emporium/products/${id}` : '/emporium'),
}

async function buildSession(): Promise<Session> {
  const agent = useAgentStore(DOMAIN)
  const cart = useCartStore(DOMAIN)
  const nav = useNavigationStore()

  const base = (useRuntimeConfig().app.baseURL || '/').replace(/\/$/, '')
  const rag = await LocalMiniSearchRAG.fromUrl(`${base}/rag/emporium-index.json`)

  const tools = referenceTools({
    rag,
    cart: buildCartHandlers(cart),
    navigate: async (target, id) => {
      const path = (ROUTES[target] ?? ROUTES.home)!(id)
      nav.recordAgentNavigation(path)
      await navigateTo(path)
    },
  })
  const registry = buildRegistry(tools)

  const session = createAgent({
    engine: await getEngine(),
    tools: registry,
    systemPrompt: () =>
      buildSystemPrompt({ persona: PERSONA, catalogHint: () => rag.hint(6), toolSchemas: registry.schemas }),
  })

  attachSessionEvents(session, agent, {
    label: DOMAIN,
    errorMessage:
      'The assistant hit a runtime error and needs to reload the model - send your message again. ' +
      'Chrome or Edge are the best-supported browsers for on-device inference.',
    onError: buildRecovery(cache),
  })
  return session
}

const cache = memoizedSession(buildSession)
export const getSession = cache.get
export const resetSession = cache.reset
