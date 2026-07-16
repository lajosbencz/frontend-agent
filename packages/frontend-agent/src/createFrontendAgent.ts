import { type Session } from './loop/agent'
import { createBoundedAgent } from './createBoundedAgent'
import { ContextManager } from './context/contextManager'
import { referenceTools, type FrontendAgentTools } from './reference/tools'
import type { AgentEngine } from './engine/types'

/** An item currently on screen. Price is a number (formatted for the model internally). */
export interface ViewSource {
  id: string
  title: string
  price: number | null
}

/** A live cart line shown to the model as CART context. */
export interface CartLineSource {
  id: string
  title: string
  quantity: number
}

/** A bounded frontend-agent deployment: you provide a `tools` mapping (one hook per frozen tool) plus
 *  the on-screen state the model grounds in. Tools can't be added or renamed - fixed trained set. */
export interface FrontendAgentConfig {
  engine: AgentEngine
  /** 1-2 lines: who the assistant is + grounding/refusal rules. */
  persona: string
  /** The items currently on screen. The model grounds in these and reaches the rest via `list_items`. */
  view: () => ViewSource[] | Promise<ViewSource[]>
  /** The live cart lines, shown to the model as CART context. Omit if the app has no cart. */
  cart?: () => CartLineSource[]
  /** One hook per frozen tool (keyed by tool name). Omit `navigate` to drop that tool from the roster. */
  tools: FrontendAgentTools

  /** VIEW sliding-window size (default 12). */
  maxViewItems?: number
  /** Max tool-loop cycles per turn (default 8). */
  maxIterations?: number
  /** Per-generation watchdog in ms (default 90s; 0 disables). */
  generationTimeoutMs?: number
}

const money = (p: number | null) => (p != null ? `$${p.toFixed(2)}` : 'n/a')

/** Build a bounded {@link Session}: each turn injects the current VIEW + CART (the trained C block)
 *  and advertises the frozen tools bound to `config.tools`. A thin shop preset over
 *  {@link createBoundedAgent} - the roster is {@link referenceTools} and the context renderer is the
 *  English VIEW/CART/KNOWLEDGE {@link ContextManager}. For a non-shop / non-English deployment, call
 *  `createBoundedAgent` directly with your own tools + context renderer. */
export function createFrontendAgent(config: FrontendAgentConfig): Session {
  const cm = new ContextManager({ persona: config.persona, maxViewItems: config.maxViewItems ?? 12 })
  let viewIds: string[] = [] // the current view's ids, so the grammar can ground bounded adds on them

  const context = async () => {
    const items = await config.view()
    viewIds = items.map((v) => v.id)
    cm.setView(items.map((v) => ({ id: v.id, title: v.title, price: money(v.price) })))
    cm.setCart((config.cart?.() ?? []).map((l) => ({ id: l.id, title: l.title, qty: l.quantity })))
    return cm.render()
  }

  return createBoundedAgent({
    engine: config.engine,
    tools: referenceTools(config.tools),
    context,
    groundingIds: () => viewIds,
    maxIterations: config.maxIterations,
    generationTimeoutMs: config.generationTimeoutMs,
  })
}
