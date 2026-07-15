import {
  renderContext,
  type CartItem,
  type ContextInput,
  type KnowledgeSnippet,
  type ViewItem,
} from './renderContext'

export interface ContextManagerConfig {
  /** Persona/rules line for this deployment. */
  persona: string
  /** Sliding-window cap on VIEW items injected per turn (most recent kept). Default 8. */
  maxViewItems?: number
  /** Cap on KNOWLEDGE snippets injected per turn. Default 4. */
  maxKnowledge?: number
}

/** Runtime side of the bounded contract: the app syncs this with the UI (view/cart/knowledge) and
 *  calls {@link render} each turn to produce the C block the stateless model grounds in. */
export class ContextManager {
  private readonly persona: string
  private readonly maxViewItems: number
  private readonly maxKnowledge: number
  private view: ViewItem[] = []
  private cart: CartItem[] | null = null
  private knowledge: KnowledgeSnippet[] = []

  constructor(cfg: ContextManagerConfig) {
    this.persona = cfg.persona
    this.maxViewItems = cfg.maxViewItems ?? 8
    this.maxKnowledge = cfg.maxKnowledge ?? 4
  }

  /** Replace the on-screen items (e.g. on navigation / search render). */
  setView(items: ViewItem[]): void {
    this.view = items
  }

  /** Set the cart. Pass `null` to omit the CART block entirely, `[]` to inject an empty cart. */
  setCart(items: CartItem[] | null): void {
    this.cart = items
  }

  /** Set the relevant knowledge snippets (policies, docs) for this turn. */
  setKnowledge(items: KnowledgeSnippet[]): void {
    this.knowledge = items
  }

  /** The C-block input after applying the sliding window - useful for inspection/tests. */
  snapshot(): ContextInput {
    return {
      persona: this.persona,
      view: this.view.slice(-this.maxViewItems),
      cart: this.cart,
      knowledge: this.knowledge.slice(0, this.maxKnowledge),
    }
  }

  /** Render the C block for this turn (windowed VIEW + CART + KNOWLEDGE). */
  render(): string {
    return renderContext(this.snapshot())
  }
}
