import type { ToolSchema } from '../tools/types'

/**
 * Generate a GBNF grammar that constrains LFM2.5 tool-call decoding to the injected tool schema.
 * TS port of training/kbft/gbnf.py (kept in lockstep - validated against llama.cpp).
 *
 * The model supplies the POLICY (which tool, when, which id semantically); the grammar GUARANTEES the
 * STRUCTURE at decode time: only valid tool names, that tool's arg keys/types, enum values, and - when
 * `validIds` (the ids present in results so far) is given - the id argument is forced to one of those,
 * so id-grounding becomes unfaultable (a truncated/hallucinated id is impossible to emit). Applied via
 * wllama's `grammar` sampling param. `allowText` keeps a free-text reply branch so normal answers work.
 */

function lit(s: string): string {
  return '"' + s.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"'
}
function sq(s: string): string {
  return lit("'" + s + "'")
}
function rn(name: string): string {
  // GBNF rule names take hyphens, not underscores
  return name.replace(/[^A-Za-z0-9]/g, '-')
}

function valueRule(
  tname: string,
  key: string,
  spec: Record<string, unknown>,
  validIds: string[] | undefined,
  idKeys: string[],
): string {
  if (idKeys.includes(key) && validIds && validIds.length) return `${rn(tname)}-${rn(key)}-id`
  const en = (spec as { enum?: unknown[] }).enum
  if (Array.isArray(en)) return '( ' + en.map((v) => sq(String(v))).join(' | ') + ' )'
  const t = (spec as { type?: string }).type
  if (t === 'integer' || t === 'number') return 'numval'
  if (t === 'boolean') return 'boolval'
  return 'strval'
}

export function buildToolGrammar(
  tools: ToolSchema[],
  validIds?: string[],
  idKeys: string[] = ['id'],
  allowText = true,
): string {
  const rules: string[] = ['sep ::= "," " "?']
  const callAlts: string[] = []
  const idAltsNeeded: [string, string][] = []

  for (const t of tools) {
    const name = t.name
    const props = (t.parameters?.properties ?? {}) as Record<string, Record<string, unknown>>
    const required = t.parameters?.required ?? []
    const r = rn(name)
    const reqFrags: string[] = []
    const optFrags: string[] = []
    for (const [key, spec] of Object.entries(props)) {
      const val = valueRule(name, key, spec, validIds, idKeys)
      if (idKeys.includes(key) && validIds && validIds.length) idAltsNeeded.push([name, key])
      const frag = `${r}-${rn(key)}`
      rules.push(`${frag} ::= ${lit(key + '=')} ${val}`)
      ;(required.includes(key) ? reqFrags : optFrags).push(frag)
    }
    // required args in order, comma-joined; optionals each appended optionally (matches the model)
    let seq = reqFrags.join(' sep ')
    for (const o of optFrags) seq = (seq ? seq + ' ' : '') + `( sep ${o} )?`
    rules.push(`${r}-call ::= ${lit(name + '(')} ${seq} ${lit(')')}`.replace(/ {2}/g, ' '))
    callAlts.push(`${r}-call`)
  }

  // One or more calls, comma-joined (`[fn1(...), fn2(...)]`); a single call is N=1. Mirrors kbft/gbnf.py.
  rules.push('call ::= ( ' + callAlts.join(' | ') + ' )')
  rules.push('toolcall ::= ' + lit('[') + ' call ( sep call )* ' + lit(']'))
  rules.push(
    'wrapped ::= ( ' + lit('<|tool_call_start|>') + ' )? toolcall ( ' + lit('<|tool_call_end|>') + ' )?',
  )
  for (const [name, key] of idAltsNeeded) {
    rules.push(`${rn(name)}-${rn(key)}-id ::= ` + (validIds as string[]).map(sq).join(' | '))
  }
  if (allowText) {
    // a free-text reply: first char isn't a tool-call opener, then any chars (incl. newlines)
    rules.push('reply ::= [^\\[<] [^\\x00]*')
    rules.push('root ::= wrapped | reply')
  } else {
    rules.push('root ::= wrapped')
  }
  rules.push(`strval ::= "'" [^']* "'"`)
  rules.push('numval ::= "-"? [0-9]+ ("." [0-9]+)?')
  rules.push('boolval ::= "True" | "False"')
  return rules.join('\n')
}

/** Collect string values under `id` keys from an arbitrary tool result (search results carry them). */
export function collectIds(value: unknown, into: Set<string>): void {
  if (Array.isArray(value)) {
    for (const v of value) collectIds(v, into)
  } else if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (k === 'id' && typeof v === 'string' && v) into.add(v)
      else collectIds(v, into)
    }
  }
}
