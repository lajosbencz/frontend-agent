import { buildToolGrammar, collectIds } from '../engine/gbnf'
import { HISTORY_TOKEN_BUDGET, estimateTokens } from '../limits'
import type { AgentEngine, ChatMessage } from '../engine/types'
import type { ToolRegistry } from '../tools/registry'

export interface ToolCall {
  name: string
  args: Record<string, unknown>
}

/** Events emitted while a turn runs. Subscribe with `session.on(...)`. */
export type AgentEvent =
  | { type: 'status'; status: 'thinking' | 'ready' | 'aborted' | 'error' }
  | { type: 'assistant'; text: string }
  | { type: 'tool_call'; call: ToolCall }
  | { type: 'tool_result'; name: string; result: unknown }
  | { type: 'done' }
  | { type: 'error'; error: unknown }

export interface AgentConfig {
  engine: AgentEngine
  /** Schemas + handlers, from `buildRegistry(referenceTools(...))` or `buildRegistry(yourTools)`. */
  tools: ToolRegistry
  /** Fixed string, or a provider called once per `submit` (receives the user turn) so the host can
   *  inject fresh context C for that turn. */
  systemPrompt: string | ((turn: { userText: string }) => string | Promise<string>)
  /** Max tool-loop cycles per turn. Default 8 (the longest trained multi-step flow). */
  maxIterations?: number
  /** Arg keys constrained to grounded ids by the grammar. Default `['id']`. */
  idKeys?: string[]
  /** Extra groundable ids beyond tool-result ids - typically the CURRENT VIEW's ids, since bounded
   *  add/remove targets live in the view, not search results. Returned fresh each turn. */
  groundingIds?: () => string[]
  /** History token budget (system prompt excluded). Default derived from N_CTX. */
  historyBudgetTokens?: number
  /** Per-generation watchdog (ms). Some WASM engines hang without rejecting (a trapped compute thread
   *  leaves the main thread on a futex forever); this surfaces it. Default 90s; 0 disables. */
  generationTimeoutMs?: number
}

class GenerationTimeoutError extends Error {
  constructor(ms: number) {
    super(`Generation timed out after ${ms}ms - the engine may have crashed or hung.`)
    this.name = 'GenerationTimeoutError'
  }
}

/** Clears the timer once either settles. */
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  if (!ms) return promise
  let timer: ReturnType<typeof setTimeout>
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new GenerationTimeoutError(ms)), ms)
  })
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer))
}

export interface SubmitOptions {
  signal?: AbortSignal
}

export interface Session {
  /** Feed user text (text box, API, STT) and run the tool loop to completion, emitting events. */
  submit(text: string, opts?: SubmitOptions): Promise<void>
  /** Abort the in-flight turn (best-effort: stops between generations/tool calls). */
  abort(): void
  /** Subscribe to events. Returns an unsubscribe function. */
  on(listener: (event: AgentEvent) => void): () => void
  /** The model-format conversation so far (assistant turns include raw tool-call markers). */
  readonly history: ChatMessage[]
  /** Clear the conversation. */
  reset(): void
}

const GIVE_UP =
  "I'm having trouble completing this - let me know if you'd like to try a simpler request."

class AbortError extends Error {
  constructor() {
    super('aborted')
    this.name = 'AbortError'
  }
}

export function createAgent(config: AgentConfig): Session {
  const maxIterations = config.maxIterations ?? 8
  const idKeys = config.idKeys ?? ['id']
  const budget = config.historyBudgetTokens ?? HISTORY_TOKEN_BUDGET
  const generationTimeoutMs = config.generationTimeoutMs ?? 90_000
  const history: ChatMessage[] = []
  const listeners = new Set<(e: AgentEvent) => void>()
  let controller: AbortController | null = null

  const emit = (e: AgentEvent) => {
    for (const l of listeners) l(e)
  }

  async function runToolCall(call: ToolCall): Promise<unknown> {
    const handler = config.tools.handlers[call.name]
    if (!handler) return { error: 'unknown_tool', name: call.name }
    try {
      return await handler(call.args)
    } catch (err) {
      return { error: 'tool_execution_failed', message: (err as Error).message }
    }
  }

  async function runLoop(system: string, signal: AbortSignal): Promise<void> {
    const seenIds = new Set<string>()
    for (let i = 0; i < maxIterations; i++) {
      if (signal.aborted) throw new AbortError()
      trimHistory(history, budget)
      const messages: ChatMessage[] = [{ role: 'system', content: system }, ...history]
      // Ground ids on BOTH tool-result ids and the current view's ids (bounded adds come from the view).
      const grounded = new Set([...seenIds, ...(config.groundingIds?.() ?? [])])
      const grammar = buildToolGrammar(
        config.tools.schemas,
        grounded.size ? [...grounded] : undefined,
        idKeys,
      )
      const result = await withTimeout(config.engine.generate(messages, grammar), generationTimeoutMs)
      if (signal.aborted) throw new AbortError()

      if (result.toolCalls.length === 0) {
        history.push({ role: 'assistant', content: result.raw })
        emit({ type: 'assistant', text: result.text })
        emit({ type: 'status', status: 'ready' })
        return
      }

      history.push({ role: 'assistant', content: result.raw })
      if (result.text) emit({ type: 'assistant', text: result.text })

      for (const call of result.toolCalls) {
        emit({ type: 'tool_call', call })
        const toolResult = await runToolCall(call)
        collectIds(toolResult, seenIds)
        emit({ type: 'tool_result', name: call.name, result: toolResult })
        history.push({ role: 'tool', content: JSON.stringify(toolResult) })
      }
    }
    history.push({ role: 'assistant', content: GIVE_UP })
    emit({ type: 'assistant', text: GIVE_UP })
    emit({ type: 'status', status: 'ready' })
  }

  return {
    history,
    on(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    abort() {
      controller?.abort()
    },
    reset() {
      history.length = 0
    },
    async submit(text, opts) {
      controller = new AbortController()
      const signal = opts?.signal
        ? AbortSignal.any([controller.signal, opts.signal])
        : controller.signal
      history.push({ role: 'user', content: text })
      emit({ type: 'status', status: 'thinking' })
      try {
        const system =
          typeof config.systemPrompt === 'function'
            ? await config.systemPrompt({ userText: text })
            : config.systemPrompt
        await runLoop(system, signal)
        emit({ type: 'done' })
      } catch (err) {
        if (err instanceof AbortError || signal.aborted) {
          emit({ type: 'status', status: 'aborted' })
          emit({ type: 'done' })
        } else {
          emit({ type: 'error', error: err })
          emit({ type: 'status', status: 'error' })
        }
      } finally {
        controller = null
      }
    },
  }
}

/** Bound history to the token budget, dropping whole oldest turns from the FRONT (never leaving a
 *  dangling `tool` continuation at the head). */
export function trimHistory(history: ChatMessage[], budget: number): void {
  const tokens = () => history.reduce((n, m) => n + estimateTokens(m.content), 0)
  while (history.length > 2 && tokens() > budget) {
    history.shift()
    // don't start the remaining history on an orphaned tool result / non-user continuation
    while (history.length > 1 && history[0]!.role === 'tool') history.shift()
  }
}
