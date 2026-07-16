// Exported prompt-parity tooling: lock a downstream deployment's runtime C-block renderer against a
// golden reference - the same guard the library uses internally via test/context-schema.fixtures.json.
// Emit fixtures from your trainer (the exact strings the tokenizer saw) and assert your runtime
// renderer reproduces them byte-for-byte, so train/runtime formats never silently drift.

/** A single parity case: feeding `input` to your renderer must produce `expected` byte-for-byte. */
export interface PromptParityCase {
  name: string
  /** Whatever your renderer takes (e.g. a `ContextInput`); opaque to this helper. */
  input: unknown
  expected: string
}

/** The golden-fixture file shape. `context_schema_version` should match the runtime renderer's
 *  `CONTEXT_SCHEMA_VERSION`; a mismatch means the format moved and fixtures must be regenerated. */
export interface PromptParityFixtures {
  context_schema_version: string
  cases: PromptParityCase[]
}

export class PromptParityError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PromptParityError'
  }
}

/** Assert the library/runtime-rendered string equals the tokenizer/golden reference, byte-for-byte.
 *  Throws a {@link PromptParityError} pointing at the first differing index on mismatch. Use in a
 *  downstream test to prove your runtime C block matches what the model was trained on. */
export function assertPromptParity(a: {
  /** The exact string the tokenizer saw at train time (from your golden fixture). */
  tokenizerRendered: string
  /** What your runtime renderer produced for the same input. */
  libRendered: string
  /** Optional case name for the error message. */
  label?: string
}): void {
  if (a.tokenizerRendered === a.libRendered) return
  const i = firstDiffIndex(a.tokenizerRendered, a.libRendered)
  throw new PromptParityError(
    `prompt parity mismatch${a.label ? ` (${a.label})` : ''} at index ${i}:\n` +
      `  trained: ${JSON.stringify(around(a.tokenizerRendered, i))}\n` +
      `  runtime: ${JSON.stringify(around(a.libRendered, i))}`,
  )
}

function firstDiffIndex(a: string, b: string): number {
  const n = Math.min(a.length, b.length)
  for (let i = 0; i < n; i++) if (a[i] !== b[i]) return i
  return n // one is a prefix of the other
}

function around(s: string, i: number): string {
  return s.slice(Math.max(0, i - 20), i + 20)
}
