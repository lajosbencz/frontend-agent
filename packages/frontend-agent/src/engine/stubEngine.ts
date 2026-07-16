import { renderToolCalls } from '../parsing/renderToolCalls'
import type { ToolRegistry } from '../tools/registry'
import type { AgentEngine, ChatMessage, EngineGenerateResult } from './types'

/** A roster-driven fixture engine (no model weights) for testing the loop/tools/UI against ANY tool
 *  set: it only emits calls for tools actually present in `registry`, falling back to the first tool
 *  that takes a `query`. Heuristic and weightless - for wiring, not fidelity. Ignores the grammar. */
export function makeStubEngine(registry: ToolRegistry): AgentEngine {
  const has = (name: string) => registry.handlers[name] != null
  const firstPresent = (...names: string[]) => names.find(has)
  const queryTool = registry.schemas.find(
    (s) => 'query' in (s.parameters.properties ?? {}),
  )?.name

  return {
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
      const addTool = firstPresent('add_to_cart')
      if (addTool && userText.includes('cart') && quotedId) {
        const quantity = Number(userText.match(/(\d+)\s*(unit|x\b)/)?.[1] ?? '1')
        return call(addTool, { id: quotedId[1], quantity })
      }
      const knowledgeTool = firstPresent('search_knowledge')
      if (knowledgeTool && /(compat|pair|guide|how|descal|clean)/.test(userText)) {
        return call(knowledgeTool, { query: userText.slice(0, 60) })
      }
      const searchTool = firstPresent('list_items') ?? queryTool
      if (searchTool && /(find|search|show|any|looking|need|grinder|machine|accessor|\?)/.test(userText)) {
        return call(searchTool, { query: userText.slice(0, 60) })
      }

      const text =
        'I can search, look things up, or act on your behalf using the available tools. What would you like to do?'
      return { text, toolCalls: [], raw: text }
    },
  }
}

/** Fixture engine hardcoded to the shop reference roster (`list_items`, `search_knowledge`,
 *  `add_to_cart`), for testing the shop preset without weights. For a custom roster use
 *  {@link makeStubEngine}, which emits calls off the tools you registered. */
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
      return call('list_items', { query: userText.slice(0, 60) })
    }

    const text =
      'I can search the catalog, look things up in the knowledge base, or manage your cart. What would you like to do?'
    return { text, toolCalls: [], raw: text }
  }
}
