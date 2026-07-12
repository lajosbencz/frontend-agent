// BrewCraft domain: espresso storefront persona, wired to its own RAG index + cart.

import { createAgent, buildRegistry, buildSystemPrompt, type Session } from '@lajosbencz/frontend-agent'
import { referenceTools } from '@lajosbencz/frontend-agent/reference'
import { LocalMiniSearchRAG } from '@lajosbencz/frontend-agent/rag'
import { useAgentStore } from '~/stores/agent'
import { useCartStore } from '~/stores/cart'
import { useNavigationStore } from '~/stores/navigation'
import { getEngine } from '../engine'
import { memoizedSession } from '../sessionCache'
import { attachSessionEvents, buildCartHandlers, buildRecovery } from './shared'

const DOMAIN = 'brewcraft'

const PERSONA =
  'You are the shopping assistant for BrewCraft, an online espresso equipment store. Use the tools to ' +
  'search the catalog and the knowledge base and to manage the cart. For a product\'s price or ' +
  'availability (whether it is in stock), search the catalog; for how-to, care, and policies, search ' +
  'the knowledge base. Ground every answer ONLY in what the tools return; if a search returns nothing ' +
  "relevant, say you don't have that information rather than guessing. Never state a product's price " +
  'or whether it is in stock unless a catalog result says so. When the user asks to add or find a ' +
  'specific item, search the catalog for THAT item first and act on the matching result. Only add ' +
  'items to the cart when the user asks. Use the exact item id from search results when calling cart tools.'

const ROUTES: Record<string, (id?: string) => string> = {
  checkout: () => '/brewcraft/checkout',
  cart: () => '/brewcraft/cart',
  home: () => '/brewcraft',
  product: (id) => (id ? `/brewcraft/products/${id}` : '/brewcraft/shop'),
}

async function buildSession(): Promise<Session> {
  const agent = useAgentStore(DOMAIN)
  const cart = useCartStore(DOMAIN)
  const nav = useNavigationStore()

  const base = (useRuntimeConfig().app.baseURL || '/').replace(/\/$/, '')
  const rag = await LocalMiniSearchRAG.fromUrl(`${base}/rag/index.json`)

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
