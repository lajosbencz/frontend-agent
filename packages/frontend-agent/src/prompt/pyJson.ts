/** Serialize like Python json.dumps defaults (", " between items, ": " after keys) - the model's
 *  chat template renders the tool list this way, so match it byte-for-byte for train/inference parity. */
export function pyJson(v: unknown): string {
  if (v === null) return 'null'
  if (typeof v === 'string') return JSON.stringify(v)
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (Array.isArray(v)) return '[' + v.map(pyJson).join(', ') + ']'
  if (typeof v === 'object') {
    const entries = Object.entries(v as Record<string, unknown>)
    return '{' + entries.map(([k, val]) => `${JSON.stringify(k)}: ${pyJson(val)}`).join(', ') + '}'
  }
  return JSON.stringify(v)
}
