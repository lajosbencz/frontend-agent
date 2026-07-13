// Domain-agnostic wllama engine singleton. One model load, shared across every domain's Session —
// expensive to reload, cheap to re-wire with a different tool registry/persona per domain.

import wllamaWasmUrl from '@wllama/wllama/esm/wasm/wllama.wasm?url'
import { CacheManager } from '@wllama/wllama'
import {
  WllamaEngine,
  resolveModelUrl,
  resolveModelRef,
  fetchModelMeta,
  type EngineStatus,
  type HFModelRef,
} from 'frontend-agent'

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

/** Reads the runtime-configurable model override (empty fields fall through to the library's own
 *  default) - used for both the actual load and the cache-check/clear below, so they always agree
 *  on which GGUF they're talking about. */
function getModelRef(): HFModelRef {
  const { modelRepo, modelVersion, modelQuant } = useRuntimeConfig().public
  const ref: HFModelRef = {}
  if (modelRepo) ref.repo = modelRepo
  if (modelVersion) ref.version = modelVersion
  if (modelQuant) ref.quant = modelQuant
  return ref
}

/** A direct GGUF URL (local or remote) if configured, else empty. Overrides the HF ref. */
function getModelUrlOverride(): string {
  return useRuntimeConfig().public.modelUrl || ''
}

/** The GGUF URL that will actually be loaded/cached - a direct `modelUrl` if set, else the resolved
 *  HF ref. Everything (load, cache check/clear, info) goes through this so they always agree. */
function getModelUrl(): string {
  return getModelUrlOverride() || resolveModelUrl(getModelRef())
}

function buildEngine(cb: EngineCallbacks): Promise<WllamaEngine> {
  const modelUrl = getModelUrlOverride()
  const engine = new WllamaEngine({
    // `modelUrl` (any local/remote URL) wins; otherwise load from the HF ref. The library treats
    // `modelUrl` as an override of `model`, so passing both would also work - we pass one for clarity.
    ...(modelUrl ? { modelUrl } : { model: getModelRef() }),
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

/** Whether the configured model's GGUF is already in the OPFS cache - no network fetch needed to load it. */
export async function isModelCached(): Promise<boolean> {
  const cache = new CacheManager()
  const name = await cache.getNameFromURL(getModelUrl())
  return (await cache.getSize(name)) >= 0
}

/** Delete the configured model's GGUF from the OPFS cache. Does not touch an already-loaded engine. */
export async function clearModelCache(): Promise<void> {
  const cache = new CacheManager()
  await cache.delete(getModelUrl())
}

/** Configured repo/version/quant, the actual served file's hash/size (a cheap HEAD, no download -
 *  the hash is what actually answers "which build did I get" for a floating ref like `main`), and
 *  the size actually sitting in the OPFS cache right now, if any. */
/** Best-effort repo/quant labels from a direct GGUF filename (`…-Q6_K.gguf`) for the settings panel. */
function describeModelUrl(url: string): { repo: string; version: string; quant: string } {
  const file = url.split('/').pop()?.replace(/\.gguf$/i, '') ?? url
  const m = file.match(/^(.*)-(Q\d[\w]*|F16|BF16)$/i)
  return { repo: m ? m[1] : file, version: 'custom', quant: m ? m[2] : '' }
}

export async function getModelInfo() {
  const override = getModelUrlOverride()
  const url = getModelUrl()
  const display = override ? describeModelUrl(override) : resolveModelRef(getModelRef())
  const cache = new CacheManager()
  const name = await cache.getNameFromURL(url)
  const [meta, diskSize] = await Promise.all([fetchModelMeta(url), cache.getSize(name)])
  return { ...display, url, ...meta, diskBytes: diskSize >= 0 ? diskSize : null }
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
