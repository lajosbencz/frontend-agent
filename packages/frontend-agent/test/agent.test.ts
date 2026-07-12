import { describe, it, expect } from 'vitest'
import { createAgent, StubEngine, buildRegistry, buildSystemPrompt } from '../src/index'
import type { AgentEvent } from '../src/index'
import { referenceTools } from '../src/reference/tools'
import type { RagBackend } from '../src/rag/types'

const rag: RagBackend = {
  async searchCatalog(query) {
    return [
      { id: 'vortex-grinder', title: 'Vortex Grinder', snippet: 'burr grinder', price: 199, in_stock: true, attrs: {}, score: 9.9 },
    ]
  },
  async searchKnowledge() {
    return [{ id: 'descaling', title: 'Descaling', snippet: 'run a descaler', score: 9.9 }]
  },
  getItem(id) {
    return id === 'vortex-grinder' ? { id, title: 'Vortex Grinder', price: 199, in_stock: true } : null
  },
}

function harness() {
  const cartState: { id: string; title: string; price: number; quantity: number }[] = []
  const cart = {
    add: (item: { id: string; title: string; price: number }, quantity: number) =>
      void cartState.push({ ...item, quantity }),
    remove: (id: string) => void cartState.splice(cartState.findIndex((c) => c.id === id), 1),
    view: () => ({ cart: cartState, total: cartState.reduce((n, c) => n + c.price * c.quantity, 0) }),
    clear: () => void (cartState.length = 0),
  }
  const tools = referenceTools({ rag, cart, navigate: () => {} })
  const registry = buildRegistry(tools)
  const engine = new StubEngine()
  const session = createAgent({
    engine,
    tools: registry,
    systemPrompt: () => buildSystemPrompt({ persona: 'P', catalogHint: () => rag.hint?.(6) ?? '', toolSchemas: registry.schemas }),
  })
  const events: AgentEvent[] = []
  session.on((e) => events.push(e))
  return { session, events, cartState, registry }
}

describe('session.submit - programmatic feed', () => {
  it('runs a search → answer loop from text input alone', async () => {
    const { session, events } = harness()
    await session.submit('find grinders')

    const types = events.map((e) => e.type)
    expect(types).toContain('tool_call')
    expect(types).toContain('tool_result')
    expect(types.at(-1)).toBe('done')

    const call = events.find((e) => e.type === 'tool_call')
    expect(call && call.type === 'tool_call' && call.call.name).toBe('search_catalog')

    const result = events.find((e) => e.type === 'tool_result')
    expect(result && result.type === 'tool_result' && (result.result as { results: unknown[] }).results.length).toBe(1)
  })

  it('records the assistant turn (with raw markers) in history', async () => {
    const { session } = harness()
    await session.submit('find grinders')
    expect(session.history[0]).toEqual({ role: 'user', content: 'find grinders' })
    expect(session.history.some((m) => m.role === 'assistant')).toBe(true)
    expect(session.history.some((m) => m.role === 'tool')).toBe(true)
  })
})

describe('reference cart tools - trained result shapes', () => {
  it('add_to_cart returns the bare trained shape (no cartItemCount)', async () => {
    const { registry, cartState } = harness()
    const out = await registry.handlers.add_to_cart!({ id: 'vortex-grinder', quantity: 2 })
    expect(out).toEqual({ ok: true, added: { id: 'vortex-grinder', title: 'Vortex Grinder', quantity: 2 } })
    expect(cartState).toEqual([{ id: 'vortex-grinder', title: 'Vortex Grinder', price: 199, quantity: 2 }])
  })

  it('add_to_cart reports not_found for unknown ids', async () => {
    const { registry } = harness()
    expect(await registry.handlers.add_to_cart!({ id: 'nope' })).toEqual({ error: 'not_found', id: 'nope' })
  })

  it('remove/clear return bare shapes', async () => {
    const { registry } = harness()
    expect(await registry.handlers.remove_from_cart!({ id: 'x' })).toEqual({ ok: true, removed: 'x' })
    expect(await registry.handlers.clear_cart!({})).toEqual({ ok: true, cleared: true })
  })
})

describe('buildSystemPrompt - v1.0.0 byte parity', () => {
  it('reproduces persona + hint + List of tools with json.dumps separators', async () => {
    const schemas = [
      { name: 'search_catalog', description: 'Search.', parameters: { type: 'object' as const, properties: { query: { type: 'string' } }, required: ['query'] } },
    ]
    const out = await buildSystemPrompt({ persona: 'You are an assistant.', catalogHint: 'A [a]; B [b]', toolSchemas: schemas })
    expect(out).toBe(
      'You are an assistant.\n\nExample catalog items: A [a]; B [b]\n' +
        'List of tools: [{"type": "function", "function": {"name": "search_catalog", "description": "Search.", ' +
        '"parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}]',
    )
  })
})

describe('generation timeout', () => {
  it('surfaces a hung/crashed engine as an error event instead of hanging forever', async () => {
    // Simulates a WASM worker that traps without ever rejecting the in-flight promise (observed
    // with wllama's multi-threaded backend): generate() never settles.
    const engine = { generate: () => new Promise<never>(() => {}) }
    const tools = buildRegistry(referenceTools({ rag, cart: { add() {}, remove() {}, view: () => ({ cart: [], total: 0 }), clear() {} }, navigate: () => {} }))
    const session = createAgent({ engine, tools, systemPrompt: 'sys', generationTimeoutMs: 20 })
    const events: AgentEvent[] = []
    session.on((e) => events.push(e))
    await session.submit('go')

    expect(events.some((e) => e.type === 'error')).toBe(true)
    expect(events.some((e) => e.type === 'status' && e.status === 'error')).toBe(true)
    const errorEvent = events.find((e) => e.type === 'error')
    expect(errorEvent && errorEvent.type === 'error' && (errorEvent.error as Error).message).toMatch(/timed out/)
  })
})

describe('abort', () => {
  it('cancels an in-flight turn between iterations', async () => {
    // an engine that always calls a tool → loops until aborted or maxIterations
    const engine = { async generate() { return { text: '', toolCalls: [{ name: 'search_catalog', args: { query: 'x' } }], raw: '' } } }
    const tools = buildRegistry(referenceTools({ rag, cart: { add() {}, remove() {}, view: () => ({ cart: [], total: 0 }), clear() {} }, navigate: () => {} }))
    const session = createAgent({ engine, tools, systemPrompt: 'sys', maxIterations: 50 })
    const events: AgentEvent[] = []
    session.on((e) => events.push(e))
    const p = session.submit('go')
    session.abort()
    await p
    expect(events.some((e) => e.type === 'status' && e.status === 'aborted')).toBe(true)
  })
})
