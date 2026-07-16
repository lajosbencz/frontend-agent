import { createFrontendAgent, type Session } from 'frontend-agent/core'
import type { FrontendAgentTools } from 'frontend-agent/reference'
import { LocalMiniSearchRAG } from 'frontend-agent/rag'
import { useAgentStore } from '~/stores/agent'
import { useCartStore } from '~/stores/cart'
import { useNavigationStore } from '~/stores/navigation'
import { getEngine, resetEngine } from '../engine'
import { memoizedSession } from '../sessionCache'

type AgentStore = ReturnType<typeof useAgentStore>

const RUNTIME_ERROR =
  'The assistant hit a runtime error and needs to reload the model - send your message again. ' +
  'Chrome or Edge are the best-supported browsers for on-device inference.'

// Fetch a domain's RAG index relative to the app base URL.
export async function loadRag(path: string): Promise<LocalMiniSearchRAG> {
  const base = (useRuntimeConfig().app.baseURL || '/').replace(/\/$/, '')
  return LocalMiniSearchRAG.fromUrl(`${base}${path}`)
}

// The three catalog/knowledge tools are identical across every domain (only the store-facing
// cart tools differ).
export function ragTools(rag: LocalMiniSearchRAG): Pick<FrontendAgentTools, 'list_items' | 'get_item' | 'search_knowledge'> {
  return {
    list_items: (query, filters) => rag.searchCatalog(query, { maxPrice: filters.max_price as number | undefined }),
    get_item: (id) => rag.getItem(id),
    search_knowledge: (query) => rag.searchKnowledge(query),
  }
}

function wireStore(session: Session, agent: AgentStore, label: string, errorMessage: string, onError: () => void): void {
  session.on((e) => {
    switch (e.type) {
      case 'assistant':
        agent.pushAssistant(e.text)
        break
      case 'tool_call':
        agent.pushToolCallNotice(e.call)
        break
      case 'tool_result':
        agent.pushToolResult(e.name, e.result)
        break
      case 'status':
        agent.status = e.status === 'thinking' ? 'thinking' : e.status === 'error' ? 'error' : 'ready'
        break
      case 'error':
        agent.status = 'error'
        agent.errorMessage = errorMessage
        console.error(`[${label}] generation failed:`, e.error)
        onError()
        break
    }
  })
}

interface DomainSpec {
  domain: string
  errorMessage?: string
  build: () => Promise<Session>
}

/** Memoize a domain Session and wire its event stream into that domain's agent store. A WASM crash
 *  can leave the shared engine broken, so recovery drops both the session cache and the engine. */
export function createDomain(spec: DomainSpec) {
  const cache = memoizedSession(async () => {
    const agent = useAgentStore(spec.domain)
    const session = await spec.build()
    wireStore(session, agent, spec.domain, spec.errorMessage ?? RUNTIME_ERROR, () => {
      cache.reset()
      void resetEngine()
    })
    return session
  })
  return { getSession: cache.get, resetSession: cache.reset }
}

interface CommerceSpec {
  domain: string
  persona: string
  ragPath: string
  /** navigate('product') fallback when no id is given. */
  shopPath: string
}

/** BrewCraft/Emporium share one storefront shape: RAG-backed catalog, a per-domain cart, and
 *  navigate/checkout routing; only persona, RAG index, and the product-list path differ. */
export function createCommerceDomain(cfg: CommerceSpec) {
  const base = `/${cfg.domain}`
  const route = (target: string, id?: string): string => {
    switch (target) {
      case 'checkout': return `${base}/checkout`
      case 'cart': return `${base}/cart`
      case 'product': return id ? `${base}/products/${id}` : cfg.shopPath
      default: return base
    }
  }
  return createDomain({
    domain: cfg.domain,
    build: async () => {
      const cart = useCartStore(cfg.domain)
      const nav = useNavigationStore()
      const rag = await loadRag(cfg.ragPath)
      return createFrontendAgent({
        engine: await getEngine(),
        persona: cfg.persona,
        view: () => rag.representativeItems(12),
        cart: () => cart.lines.map((l) => ({ id: l.slug, title: l.title, quantity: l.quantity })),
        tools: {
          ...ragTools(rag),
          add_to_cart: (item, quantity) => cart.add({ slug: item.id, title: item.title, price: item.price }, quantity),
          remove_from_cart: (id) => cart.remove(id),
          clear_cart: () => cart.clear(),
          checkout: async () => {
            const receipt = { items: cart.lines.map((l) => ({ id: l.slug, title: l.title, price: l.price, quantity: l.quantity })), total: cart.total }
            nav.recordAgentNavigation(route('checkout'))
            await navigateTo(route('checkout'))
            return { ok: true, receipt }
          },
          navigate: async (target, id) => {
            const path = route(target, id)
            nav.recordAgentNavigation(path)
            await navigateTo(path)
          },
        },
      })
    },
  })
}
