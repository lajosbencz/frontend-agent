export interface ParsedToolCall {
  name: string
  args: Record<string, unknown>
}

export interface ParseResult {
  text: string
  toolCalls: ParsedToolCall[]
}

const CALL_BLOCK_RE = /<\|tool_call_start\|>([\s\S]*?)<\|tool_call_end\|>/g

/**
 * Extracts pythonic tool calls (e.g. `[search_products(query="x"), add_to_cart(slug="y", quantity=2)]`)
 * from LFM2.5's tool_call_start/end markers, and returns the remaining plain text.
 * Never uses eval - parses the restricted call grammar by hand.
 */
export function parseToolCalls(raw: string): ParseResult {
  const toolCalls: ParsedToolCall[] = []
  const text = raw.replace(CALL_BLOCK_RE, (_match, inner: string) => {
    toolCalls.push(...parseCallList(inner.trim()))
    return ''
  })
  return { text: text.trim(), toolCalls }
}

function parseCallList(block: string): ParsedToolCall[] {
  const inner = block.startsWith('[') && block.endsWith(']') ? block.slice(1, -1) : block
  const calls: ParsedToolCall[] = []
  for (const piece of splitTopLevel(inner, ',')) {
    const trimmed = piece.trim()
    if (!trimmed) continue
    const call = parseSingleCall(trimmed)
    if (call) calls.push(call)
  }
  return calls
}

function parseSingleCall(expr: string): ParsedToolCall | null {
  const match = expr.match(/^([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)$/s)
  if (!match) return null
  const [, name, argsSrc] = match
  const args: Record<string, unknown> = {}
  for (const piece of splitTopLevel(argsSrc, ',')) {
    const trimmed = piece.trim()
    if (!trimmed) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    const valueSrc = trimmed.slice(eq + 1).trim()
    args[key] = parseValue(valueSrc)
  }
  return { name, args }
}

function parseValue(src: string): unknown {
  if (src === 'True') return true
  if (src === 'False') return false
  if (src === 'None') return null
  if (/^-?\d+$/.test(src)) return parseInt(src, 10)
  if (/^-?\d+\.\d+$/.test(src)) return parseFloat(src)
  if (
    (src.startsWith('"') && src.endsWith('"')) ||
    (src.startsWith("'") && src.endsWith("'"))
  ) {
    return src.slice(1, -1)
  }
  return src
}

/** Splits on a delimiter, ignoring delimiters inside quotes/parens/brackets. */
function splitTopLevel(src: string, delimiter: string): string[] {
  const parts: string[] = []
  let depth = 0
  let quote: string | null = null
  let current = ''
  for (const ch of src) {
    if (quote) {
      current += ch
      if (ch === quote) quote = null
      continue
    }
    if (ch === '"' || ch === "'") {
      quote = ch
      current += ch
      continue
    }
    if (ch === '(' || ch === '[') depth++
    if (ch === ')' || ch === ']') depth--
    if (ch === delimiter && depth === 0) {
      parts.push(current)
      current = ''
      continue
    }
    current += ch
  }
  if (current.trim()) parts.push(current)
  return parts
}
