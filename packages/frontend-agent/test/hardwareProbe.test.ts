import { describe, expect, it } from 'vitest'
import { probeHardware, MIN_GFLOPS } from '../src/engine/hardwareProbe'
import { MM_WASM_B64 } from '../src/engine/mm.generated'

// Functional guard for the embedded probe kernel - needs no compiler, so it runs in any CI. Proves the
// committed mm.generated.ts still instantiates and produces a sane throughput number.
describe('hardware probe', () => {
  it('embedded kernel instantiates and computes', async () => {
    const bytes = Uint8Array.from(atob(MM_WASM_B64), (c) => c.charCodeAt(0))
    const { instance } = await WebAssembly.instantiate(bytes, {})
    const mm = (instance.exports as { mm: (n: number, i: number) => number }).mm
    expect(typeof mm).toBe('function')
    expect(Number.isFinite(mm(64, 4))).toBe(true)
  })

  it('probeHardware returns a positive GFLOPS and a boolean verdict', async () => {
    const p = await probeHardware()
    expect(p.gflops).toBeGreaterThan(0)
    expect(typeof p.subpar).toBe('boolean')
    // CI runners are healthy; with no WebGPU the verdict hinges on the threshold - just assert coherence.
    expect(p.subpar).toBe(!p.webgpu && p.gflops != null && p.gflops < MIN_GFLOPS)
  })
})
