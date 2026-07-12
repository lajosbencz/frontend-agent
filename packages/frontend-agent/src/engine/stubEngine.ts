import { renderToolCalls } from '../parsing/renderToolCalls'
import type { AgentEngine, ChatMessage, EngineGenerateResult } from './types'

/**
 * Fixture engine with no model weights - for building/testing the loop, tools, and UI without
 * loading the real model. Emits calls on the current v1.0.0 contract (`search_catalog`,
 * `search_knowledge`, `add_to_cart(id)`). Ignores the grammar.
 */
export class StubEngine implements AgentEngine {
  async generate(messages: ChatMessage[], _grammar?: string): Promise<EngineGenerateResult> {
    void _grammar
    const lastUserIdx = messages.map((m) => m.role).lastIndexOf('user')
    const trailingToolResults = messages.slice(lastUserIdx + 1).filter((m) => m.role === 'tool')
    const userText = (messages[lastUserIdx]?.content ?? '').toLowerCase()

    if (trailingToolResults.length > 0) {
      const last = trailingToolResults[trailingToolResults.length - 1]
      const text = `Here's what I found: ${last?.content ?? ''}`
      return { text, toolCalls: [], raw: text }
    }

    const call = (name: string, args: Record<string, unknown>): EngineGenerateResult => {
      const toolCalls = [{ name, args }]
      return { text: '', toolCalls, raw: renderToolCalls(toolCalls) }
    }

    const quotedId = userText.match(/['"]([a-z0-9-]+)['"]/)
    if (userText.includes('cart') && quotedId) {
      const quantity = Number(userText.match(/(\d+)\s*(unit|x\b)/)?.[1] ?? '1')
      return call('add_to_cart', { id: quotedId[1], quantity })
    }
    if (/(compat|pair|guide|how|descal|clean)/.test(userText)) {
      return call('search_knowledge', { query: userText.slice(0, 60) })
    }
    if (/(find|search|show|any|looking|need|grinder|machine|accessor)/.test(userText)) {
      return call('search_catalog', { query: userText.slice(0, 60) })
    }

    const text =
      'I can search the catalog, look things up in the knowledge base, or manage your cart. What would you like to do?'
    return { text, toolCalls: [], raw: text }
  }
}
