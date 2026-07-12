import { getEngine, resetEngine, isModelCached, clearModelCache } from '~/lib/agent/engine'

// Lets the root picker page warm up the shared engine before the user opens a domain, so the
// first message in whichever demo they pick doesn't stall on a cold load. Module-level singleton
// state (mirrors the speech composables) so the button reflects reality wherever it's rendered.

export type PreloadStatus = 'idle' | 'downloading' | 'ready' | 'error'

const status = ref<PreloadStatus>('idle')
const cached = ref<boolean | null>(null)
const progress = ref<{ bytesLoaded: number; bytesTotal: number } | null>(null)
const errorMessage = ref<string | null>(null)
let checked = false

export function useModelPreload() {
  async function checkCached() {
    if (checked || !import.meta.client) return
    checked = true
    try {
      cached.value = await isModelCached()
    } catch {
      cached.value = null
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

  return { status, cached, progress, errorMessage, checkCached, preload, unload, clearCache }
}
