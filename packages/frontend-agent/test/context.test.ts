import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import {
  CONTEXT_SCHEMA_VERSION,
  ContextManager,
  renderContext,
  type ContextInput,
} from '../src/context'

// The C-block contract is shared with the Python trainer via golden fixtures. This asserts the TS
// renderer reproduces them byte-for-byte and the version agrees; if it fails, the runtime and the
// trained format have drifted (regenerate fixtures + bump CONTEXT_SCHEMA_VERSION on BOTH sides).
const fixturesUrl = new URL('./context-schema.fixtures.json', import.meta.url)
const fixtures = JSON.parse(readFileSync(fileURLToPath(fixturesUrl), 'utf8')) as {
  context_schema_version: string
  cases: { name: string; input: ContextInput; expected: string }[]
}

describe('renderContext conformance (shared fixtures)', () => {
  it('version matches the fixtures', () => {
    expect(CONTEXT_SCHEMA_VERSION).toBe(fixtures.context_schema_version)
  })

  for (const c of fixtures.cases) {
    it(`renders "${c.name}" byte-for-byte`, () => {
      expect(renderContext(c.input)).toBe(c.expected)
    })
  }
})

describe('ContextManager', () => {
  it('windows the view to the most recent maxViewItems', () => {
    const cm = new ContextManager({ persona: 'P', maxViewItems: 2 })
    cm.setView([
      { id: 'a', title: 'A', price: '$1' },
      { id: 'b', title: 'B', price: '$2' },
      { id: 'c', title: 'C', price: '$3' },
    ])
    const snap = cm.snapshot()
    expect(snap.view?.map((v) => v.id)).toEqual(['b', 'c'])
    expect(cm.render()).toContain('1. B [b] - $2')
    expect(cm.render()).not.toContain('[a]')
  })

  it('omits CART when null, renders empty when []', () => {
    const cm = new ContextManager({ persona: 'P' })
    expect(cm.render()).toBe('P')
    cm.setCart([])
    expect(cm.render()).toBe('P\n\nCART: empty')
  })
})
