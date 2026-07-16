// Domain-agnostic wllama engine singleton: one model load shared across every domain's Session,
// cheap to re-wire with a different tool registry/persona per domain.

import wllamaWasmUrl from '@wllama/wllama/esm/wasm/wllama.wasm?url'
// Prebuilt ESM entry, not the bare package root (its package.json main points at a nonexistent root
// index.js; only raw index.ts ships there). Keeps the demo off untranspiled TS - same rule the lib follows.
import { CacheManager } from '@wllama/wllama/esm/index.js'
import {
  WllamaEngine,
  resolveModelUrl,
  resolveModelRef,
  fetchModelMeta,
  type EngineStatus,
  type HFModelRef,
} from 'frontend-agent/wllama'

export interface EngineCallbacks {
  onStatus?: (status: EngineStatus) => void
  onProgress?: (progress: { loaded: number; total: number }) => void
  onBackend?: (info: { webgpu: boolean; using: 'webgpu' | 'cpu' }) => void
}

let enginePromise: Promise<WllamaEngine> | null = null
let backendPref: 'auto' | 'webgpu' | 'cpu' = 'auto'
let lastBackend: { webgpu: boolean; using: 'webgpu' | 'cpu' } | null = null
// Dropdown selection: when set it wins over the runtimeConfig ref and the self-host modelUrl.
let modelRefOverride: HFModelRef | null = null
const resetListeners = new Set<() => void>()

/** Set the runtime-selected model. Does NOT reload - the caller drives resetEngine()/getEngine(). */
export function setModelOverride(ref: HFModelRef | null): void {
  modelRefOverride = ref
}

// Serialize every engine lifecycle op onto one chain so a load never overlaps a teardown: at most
// one wllama model resident at a time.
let opLock: Promise<unknown> = Promise.resolve()
function serialize<T>(fn: () => Promise<T>): Promise<T> {
  const run = opLock.then(fn, fn)
  opLock = run.then(() => {}, () => {})
  return run
}

/** Domain session caches subscribe here so a backend/model switch invalidates them (they hold the old engine). */
export function onEngineReset(cb: () => void): void {
  resetListeners.add(cb)
}

/** The model ref to load: dropdown override, else runtimeConfig, else the library default. */
function getModelRef(): HFModelRef {
  if (modelRefOverride) return modelRefOverride
  const { modelRepo, modelVersion, modelQuant } = useRuntimeConfig().public
  const ref: HFModelRef = {}
  if (modelRepo) ref.repo = modelRepo
  if (modelVersion) ref.version = modelVersion
  if (modelQuant) ref.quant = modelQuant
  return ref
}

/** A direct self-host GGUF URL if configured; overrides the HF ref. */
function getModelUrlOverride(): string {
  return useRuntimeConfig().public.modelUrl || ''
}

/** The GGUF URL actually loaded/cached; everything (load, cache, info) routes through this so they agree. */
function getModelUrl(): string {
  if (modelRefOverride) return resolveModelUrl(modelRefOverride)
  return getModelUrlOverride() || resolveModelUrl(getModelRef())
}

function buildEngine(cb: EngineCallbacks): Promise<WllamaEngine> {
  const modelUrl = modelRefOverride ? '' : getModelUrlOverride() // a dropdown pick wins over self-host
  const engine = new WllamaEngine({
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

/** Load (or reuse) the shared engine, replaying known backend/ready state if already loaded. */
export function getEngine(cb: EngineCallbacks = {}): Promise<WllamaEngine> {
  if (!enginePromise) {
    enginePromise = serialize(() => buildEngine(cb)) // queues behind any pending teardown
  } else if (lastBackend) {
    cb.onBackend?.(lastBackend)
    cb.onStatus?.('ready')
  }
  return enginePromise
}

/** Whether the configured model's GGUF is already in the OPFS cache. */
export async function isModelCached(): Promise<boolean> {
  const cache = new CacheManager()
  const name = await cache.getNameFromURL(getModelUrl())
  return (await cache.getSize(name)) >= 0
}

/** Delete the configured model's GGUF from the OPFS cache. Does not touch a resident engine. */
export async function clearModelCache(): Promise<void> {
  const cache = new CacheManager()
  await cache.delete(getModelUrl())
}

/** Delete EVERY cached GGUF from OPFS (all models/quants/versions). Leaves a resident engine running. */
export async function clearAllModelCaches(): Promise<void> {
  const cache = new CacheManager()
  await cache.clear()
}

/** Best-effort repo/quant labels from a direct GGUF filename (`...-Q6_K.gguf`), for a self-host URL. */
function describeModelUrl(url: string): { repo: string; version: string; quant: string } {
  const file = url.split('/').pop()?.replace(/\.gguf$/i, '') ?? url
  const m = file.match(/^(.*)-(Q\d[\w]*|F16|BF16)$/i)
  return { repo: m ? m[1] : file, version: 'custom', quant: m ? m[2] : '' }
}

/** Repo/version/quant labels + the served file's hash/size (cheap HEAD) + any OPFS-cached size. */
export async function getModelInfo() {
  const override = getModelUrlOverride()
  const url = getModelUrl()
  const display = override ? describeModelUrl(override) : resolveModelRef(getModelRef())
  const cache = new CacheManager()
  const name = await cache.getNameFromURL(url)
  const [meta, diskSize] = await Promise.all([fetchModelMeta(url), cache.getSize(name)])
  return { ...display, url, ...meta, diskBytes: diskSize >= 0 ? diskSize : null }
}

/** Tear down and reload the engine (backend/model switch). OPFS-cached, so no re-download. */
export async function resetEngine(pref?: 'auto' | 'webgpu' | 'cpu'): Promise<void> {
  if (pref) backendPref = pref
  const p = enginePromise
  enginePromise = null // a concurrent getEngine() now queues a fresh build behind this teardown
  lastBackend = null
  await serialize(async () => {
    const e = p ? await p.catch(() => null) : null
    await e?.reset()
  })
  resetListeners.forEach((cb) => cb())
}
