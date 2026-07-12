import type { ParsedToolCall } from './toolCallParser'

// Inverse of toolCallParser: render parsed calls back into the exact LFM2.5 wire format
// (mirrors the chat template's render_tool_calls macro) so a tool-call turn can be replayed
// verbatim into the next generation's context.

function formatArg(value: unknown): string {
  if (typeof value === 'string') return `'${value}'`
  if (value === null) return 'None'
  if (typeof value === 'boolean') return value ? 'True' : 'False'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function renderToolCalls(calls: ParsedToolCall[]): string {
  const rendered = calls.map((c) => {
    const args = Object.entries(c.args)
      .map(([k, v]) => `${k}=${formatArg(v)}`)
      .join(', ')
    return `${c.name}(${args})`
  })
  return `<|tool_call_start|>[${rendered.join(', ')}]<|tool_call_end|>`
}
