// Domain-agnostic wllama engine singleton. One model load, shared across every domain's Session —
// expensive to reload, cheap to re-wire with a different tool registry/persona per domain.

import wllamaWasmUrl from '@wllama/wllama/esm/wasm/wllama.wasm?url'
import { CacheManager } from '@wllama/wllama'
import { WllamaEngine, resolveModelUrl, type EngineStatus } from '@lajosbencz/frontend-agent'

export interface EngineCallbacks {
  onStatus?: (status: EngineStatus) => void
  onProgress?: (progress: { loaded: number; total: number }) => void
  onBackend?: (info: { webgpu: boolean; using: 'webgpu' | 'cpu' }) => void
}

let enginePromise: Promise<WllamaEngine> | null = null
let backendPref: 'auto' | 'webgpu' | 'cpu' = 'auto'
let lastBackend: { webgpu: boolean; using: 'webgpu' | 'cpu' } | null = null
const resetListeners = new Set<() => void>()

/** Domain session caches subscribe here so a backend switch invalidates them too (they hold the old engine). */
export function onEngineReset(cb: () => void): void {
  resetListeners.add(cb)
}

function buildEngine(cb: EngineCallbacks): Promise<WllamaEngine> {
  const engine = new WllamaEngine({
    wllamaAssets: { default: wllamaWasmUrl },
    backend: backendPref,
    onStatus: (s) => cb.onStatus?.(s),
    onProgress: (p) => cb.onProgress?.(p),
    onBackend: (b) => {
      lastBackend = b
      cb.onBackend?.(b)
    },
  })
  return engine.load().then(() => engine)
}

/** Load (or reuse) the shared engine. If already loaded, immediately replays known backend/ready state. */
export function getEngine(cb: EngineCallbacks = {}): Promise<WllamaEngine> {
  if (!enginePromise) {
    enginePromise = buildEngine(cb)
  } else if (lastBackend) {
    cb.onBackend?.(lastBackend)
    cb.onStatus?.('ready')
  }
  return enginePromise
}

/** Whether the default model's GGUF is already in the OPFS cache - no network fetch needed to load it. */
export async function isModelCached(): Promise<boolean> {
  const cache = new CacheManager()
  const name = await cache.getNameFromURL(resolveModelUrl())
  return (await cache.getSize(name)) >= 0
}

/** Delete the default model's GGUF from the OPFS cache. Does not touch an already-loaded engine. */
export async function clearModelCache(): Promise<void> {
  const cache = new CacheManager()
  await cache.delete(resolveModelUrl())
}

/** Tear down and reload the engine (e.g. on a backend switch). OPFS-cached, so no re-download. */
export async function resetEngine(pref?: 'auto' | 'webgpu' | 'cpu'): Promise<void> {
  if (pref) backendPref = pref
  const p = enginePromise
  enginePromise = null
  lastBackend = null
  const e = p ? await p.catch(() => null) : null
  await e?.reset()
  resetListeners.forEach((cb) => cb())
}
