/**
 * Serialize a value the way Python's json.dumps (and Jinja2's `tojson`) does by default:
 * ", " between items and ": " after keys. The model's chat template renders the tool list
 * with these separators, so the browser must match them byte-for-byte for train/inference
 * parity. (Our tool schemas are ASCII with no <,>,& so htmlsafe escaping never triggers.)
 */
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
