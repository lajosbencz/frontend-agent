import type { Session } from '@lajosbencz/frontend-agent'
import type { CartHandlers } from '@lajosbencz/frontend-agent/reference'
import { useAgentStore } from '~/stores/agent'
import { useCartStore } from '~/stores/cart'
import { resetEngine } from '../engine'

type AgentStore = ReturnType<typeof useAgentStore>
type CartStore = ReturnType<typeof useCartStore>

/** Standard cart wiring shared by every domain with a real cart page (BrewCraft, Emporium) - maps
 *  the trained add/remove/view/clear shape onto a Pinia cart store. Vendor has its own counter
 *  semantics (see domains/vendor.ts) so it doesn't use this. */
export function buildCartHandlers(cart: CartStore): CartHandlers {
  return {
    add: (item, quantity) => cart.add({ slug: item.id, title: item.title, price: item.price }, quantity),
    remove: (id) => cart.remove(id),
    view: () => ({
      cart: cart.lines.map((l) => ({ id: l.slug, title: l.title, price: l.price, quantity: l.quantity })),
      total: cart.total,
    }),
    clear: () => cart.clear(),
  }
}

/** The shared engine (and any other domain sharing it) may be left in a broken state by a WASM
 *  crash - force a fresh reload on next use rather than retrying against a dead worker. Identical
 *  recovery across every domain; only the session cache to invalidate differs. */
export function buildRecovery(cache: { reset: () => void }): () => void {
  return () => {
    cache.reset()
    void resetEngine()
  }
}

export interface SessionEventOptions {
  /** Used in the console.error label, e.g. `[vendor] generation failed: ...`. */
  label: string
  /** Shown to the user in the panel/dialogue when a generation error occurs. */
  errorMessage: string
  /** Called after the error is recorded - typically resets the engine/session cache for recovery. */
  onError: () => void
}

/** Wire a Session's event stream into a domain's agent store. Identical across every domain - only
 *  the error copy and recovery action differ, so those are passed in rather than duplicated. */
export function attachSessionEvents(session: Session, agent: AgentStore, opts: SessionEventOptions): void {
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
        agent.errorMessage = opts.errorMessage
        console.error(`[${opts.label}] generation failed:`, e.error)
        opts.onError()
        break
    }
  })
}
