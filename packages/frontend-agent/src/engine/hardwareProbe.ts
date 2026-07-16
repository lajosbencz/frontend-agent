// Pre-load hardware probe: a ~150ms single-thread WASM matmul (a 64x64 f32 GEMM in a tight loop)
// yields a rough CPU throughput number (GFLOPS) that predicts on-device decode speed far better than
// any static spec the browser exposes (there is no CPU-clock API; navigator.deviceMemory is coarse).
// Combined with WebGPU presence + core count, the host can warn BEFORE downloading the model that a
// device is likely too slow. Heuristic and coarse - a gate, not a benchmark. No heavy deps (core).
//
// The kernel is compiled from assembly/matmul.ts by `npm run build:wasm` into mm.generated.ts.

import { MM_WASM_B64 } from './mm.generated'

/** Below this single-thread WASM matmul throughput, on-device (CPU/WASM) decoding is likely too slow
 *  to feel responsive. Calibrated against a Ryzen 9 9900X measuring ~5.5 GFLOPS with this exact kernel
 *  (Node/V8 == Chrome engine); the threshold is ~36% of that, so mid-range machines pass and only weak
 *  CPUs trip it. Tune here if field data warrants. Ignored when a WebGPU fast path is present. */
export const MIN_GFLOPS = 2

export interface HardwareProbe {
  /** Single-thread WASM matmul throughput (GFLOPS), or null if the probe could not run. */
  gflops: number | null
  /** navigator.hardwareConcurrency (logical cores), or 0 if unknown. */
  cores: number
  /** A usable WebGPU adapter is present (the fast decode path). */
  webgpu: boolean
  /** Recommendation to warn the user before loading: no WebGPU AND CPU below {@link MIN_GFLOPS}.
   *  Fail-open: if the probe could not measure, this is `false` (never warn on a false negative). */
  subpar: boolean
}

function bytesFromBase64(b64: string): Uint8Array {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

async function hasWebGPU(): Promise<boolean> {
  try {
    const gpu = (globalThis.navigator as unknown as {
      gpu?: { requestAdapter?: () => Promise<unknown> }
    })?.gpu
    if (!gpu?.requestAdapter) return false
    return (await gpu.requestAdapter()) != null
  } catch {
    return false
  }
}

/** Measure single-thread WASM matmul throughput. Adapts the iteration count to land near ~120ms, then
 *  takes the fastest of 3 runs (least scheduler noise). Returns null if WASM is unavailable. */
function measureGflops(): number | null {
  if (typeof WebAssembly === 'undefined' || typeof performance === 'undefined') return null
  try {
    const mod = new WebAssembly.Module(bytesFromBase64(MM_WASM_B64) as BufferSource)
    const inst = new WebAssembly.Instance(mod, {})
    const mm = (inst.exports as { mm: (n: number, iters: number) => number }).mm
    const n = 64
    const flopsPerIter = 2 * n * n * n

    mm(n, 40) // warm the JIT / caches

    // Calibrate iters toward ~120ms so both slow and fast CPUs get a stable window.
    let iters = 200
    for (let i = 0; i < 6; i++) {
      const t0 = performance.now()
      mm(n, iters)
      const dt = performance.now() - t0
      if (dt > 80 && dt < 400) break
      iters = Math.max(20, Math.min(200000, Math.round((iters * 120) / Math.max(dt, 0.5))))
    }

    let best = 0
    for (let r = 0; r < 3; r++) {
      const t0 = performance.now()
      mm(n, iters)
      const dt = performance.now() - t0
      if (dt > 0) best = Math.max(best, (flopsPerIter * iters) / dt / 1e6) // 2*n^3*iters flops/ms -> GFLOPS
    }
    return best || null
  } catch {
    return null
  }
}

/** Probe device capability before loading the model. Runs a ~150ms CPU benchmark, checks WebGPU and
 *  core count, and returns whether to warn about likely-slow on-device inference. Safe to call once at
 *  startup; costs a few hundred ms and downloads nothing. `minGflops` overrides {@link MIN_GFLOPS}. */
export async function probeHardware(opts?: { minGflops?: number }): Promise<HardwareProbe> {
  const minGflops = opts?.minGflops ?? MIN_GFLOPS
  const cores =
    (globalThis.navigator as { hardwareConcurrency?: number } | undefined)?.hardwareConcurrency ?? 0
  const webgpu = await hasWebGPU()
  const gflops = measureGflops()
  const subpar = !webgpu && gflops != null && gflops < minGflops
  return { gflops, cores, webgpu, subpar }
}
