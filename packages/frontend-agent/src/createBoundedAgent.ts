import { createAgent, type Session } from './loop/agent'
import { buildRegistry } from './tools/registry'
import { buildSystemPrompt } from './prompt/systemPrompt'
import type { AgentEngine } from './engine/types'
import type { ToolDefinition } from './tools/types'

/** Domain-neutral bounded-agent factory: you bring the roster and the C-block renderer. Nothing here
 *  assumes a shop, a cart, money, or English - `createFrontendAgent` is just a preset over this. */
export interface BoundedAgentConfig {
  engine: AgentEngine
  /** Your tool roster (any tools - not the frozen reference set). Dispatched in array order; order is
   *  contract-significant (it is the order advertised in the system prompt). */
  tools: ToolDefinition[]
  /** Render the turn's context block C - persona plus whatever state you inject, in YOUR format and
   *  language. A fixed string, or a provider called once per `submit` (receives the user turn). This
   *  is the brittle train/runtime contract: it must match what the model was trained on. */
  context: string | ((turn: { userText: string }) => string | Promise<string>)
  /** Any ids the model may reference that won't appear in tool results (e.g. items already on screen).
   *  Returned fresh each turn and folded into the grammar's id-grounding. */
  groundingIds?: () => string[]
  /** Optional "headline entities" hint appended after the context (see {@link buildSystemPrompt}). */
  catalogHint?: string | (() => string | Promise<string>)
  /** Label before the hint. Defaults to the trained `"Example catalog items"`. */
  hintLabel?: string
  /** Arg keys the grammar constrains to grounded ids. Default `['id']`. */
  idKeys?: string[]
  /** Max tool-loop cycles per turn (default 8). */
  maxIterations?: number
  /** Per-generation watchdog in ms (default 90s; 0 disables). */
  generationTimeoutMs?: number
}

/** Build a bounded {@link Session} from your roster + context renderer: each turn renders C via
 *  `context`, advertises `tools`, and grounds ids on tool results + `groundingIds`. */
export function createBoundedAgent(cfg: BoundedAgentConfig): Session {
  const registry = buildRegistry(cfg.tools)
  const systemPrompt = async (turn: { userText: string }) => {
    const persona = typeof cfg.context === 'function' ? await cfg.context(turn) : cfg.context
    return buildSystemPrompt({
      persona,
      toolSchemas: registry.schemas,
      catalogHint: cfg.catalogHint,
      hintLabel: cfg.hintLabel,
    })
  }
  return createAgent({
    engine: cfg.engine,
    tools: registry,
    systemPrompt,
    groundingIds: cfg.groundingIds,
    idKeys: cfg.idKeys,
    maxIterations: cfg.maxIterations,
    generationTimeoutMs: cfg.generationTimeoutMs,
  })
}
