import { probeHardware, MIN_GFLOPS, type HardwareProbe } from 'frontend-agent/core'
import {
  getEngine,
  resetEngine,
  isModelCached,
  clearModelCache,
  clearAllModelCaches,
} from '~/lib/agent/engine'

// Lets the root picker page warm up the shared engine before the user opens a domain, so the
// first message in whichever demo they pick doesn't stall on a cold load. Module-level singleton
// state (mirrors the speech composables) so the button reflects reality wherever it's rendered.

export type PreloadStatus = 'idle' | 'downloading' | 'ready' | 'error'

const status = ref<PreloadStatus>('idle')
const cached = ref<boolean | null>(null)
const progress = ref<{ bytesLoaded: number; bytesTotal: number } | null>(null)
const errorMessage = ref<string | null>(null)
const hardware = ref<HardwareProbe | null>(null)
let checked = false

const HW_KEY = 'fa:hw-probe'
const HW_SCHEMA = 1

function readCachedHardware(): HardwareProbe | null {
  try {
    const raw = localStorage.getItem(HW_KEY)
    if (!raw) return null
    const o = JSON.parse(raw)
    if (o?.v !== HW_SCHEMA || typeof o.gflops !== 'number') return null
    return {
      gflops: o.gflops,
      cores: typeof o.cores === 'number' ? o.cores : 0,
      webgpu: !!o.webgpu,
      subpar: !o.webgpu && o.gflops < MIN_GFLOPS,
    }
  } catch {
    return null
  }
}

function writeCachedHardware(p: HardwareProbe): void {
  try {
    localStorage.setItem(
      HW_KEY,
      JSON.stringify({ v: HW_SCHEMA, gflops: p.gflops, cores: p.cores, webgpu: p.webgpu }),
    )
  } catch {
    /* private mode / quota - just re-probe next time */
  }
}

export function useModelPreload() {
  async function checkCached() {
    if (checked || !import.meta.client) return
    checked = true
    try {
      cached.value = await isModelCached()
    } catch {
      cached.value = null
    }
    const cachedHw = readCachedHardware()
    if (cachedHw) {
      hardware.value = cachedHw
    } else {
      try {
        const probed = await probeHardware()
        hardware.value = probed
        if (probed.gflops != null) writeCachedHardware(probed)
      } catch {
        hardware.value = null
      }
    }
  }

  async function preload() {
    if (status.value === 'downloading' || status.value === 'ready') return
    status.value = 'downloading'
    errorMessage.value = null
    try {
      await getEngine({
        onProgress: ({ loaded, total }) => {
          progress.value = { bytesLoaded: loaded, bytesTotal: total }
        },
      })
      status.value = 'ready'
      cached.value = true
    } catch (err) {
      status.value = 'error'
      errorMessage.value = "Couldn't load the model in this browser - try Chrome or Edge."
      console.error('[model-preload] failed:', err)
    }
  }

  /** Tear the in-memory engine down (any domain's next message reloads it - instantly, if still cached). */
  async function unload() {
    if (status.value !== 'ready') return
    await resetEngine()
    status.value = 'idle'
    progress.value = null
  }

  /** Delete the cached GGUF from OPFS. Leaves an already-loaded engine running until it's unloaded. */
  async function clearCache() {
    if (!cached.value) return
    try {
      await clearModelCache()
      cached.value = false
    } catch (err) {
      errorMessage.value = 'Failed to clear the cached model.'
      console.error('[model-preload] cache clear failed:', err)
    }
  }

  /** Delete every cached GGUF from OPFS (all models/quants/versions). Leaves a resident engine running. */
  async function clearAllCaches() {
    try {
      await clearAllModelCaches()
      cached.value = false
    } catch (err) {
      errorMessage.value = 'Failed to clear the downloaded models.'
      console.error('[model-preload] clear-all failed:', err)
    }
  }

  /** After the selected model changed (engine torn down, new pick not yet loaded): reset to idle and
   *  re-check whether the newly selected model's GGUF is already cached. */
  async function syncToSelection() {
    status.value = 'idle'
    progress.value = null
    errorMessage.value = null
    try {
      cached.value = await isModelCached()
    } catch {
      cached.value = null
    }
  }

  return {
    status, cached, progress, errorMessage, hardware,
    checkCached, preload, unload, clearCache, clearAllCaches, syncToSelection,
  }
}
