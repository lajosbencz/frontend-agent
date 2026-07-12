import { getEngine, resetEngine, type EngineCallbacks } from '~/lib/agent/engine'

// Module-level singleton (mirrors useModelPreload/useSpeech*) so the GPU/CPU preference and its
// resolved state are shared by every consumer - the chat panel's toggle and the index page's
// toggle drive and reflect the exact same setting, with no per-domain duplication.

export type BackendKind = 'webgpu' | 'cpu'
export type BackendPref = BackendKind | 'auto'

const backend = ref<BackendKind | null>(null)
const webgpuAvailable = ref<boolean | null>(null)
const pref = ref<BackendPref>('auto')
const switching = ref(false)

export function useBackend() {
  const noteBackend: EngineCallbacks['onBackend'] = (info) => {
    webgpuAvailable.value = info.webgpu
    backend.value = info.using
  }

  /** Switch preference. Reloads eagerly only if an engine was already resolved/loading. */
  async function setPref(next: BackendPref) {
    if (pref.value === next || switching.value) return
    pref.value = next
    const wasLoaded = backend.value !== null
    switching.value = true
    if (wasLoaded) backend.value = null
    try {
      await resetEngine(next)
      if (wasLoaded) await getEngine({ onBackend: noteBackend })
    } finally {
      switching.value = false
    }
  }

  function toggle() {
    const current = backend.value ?? (pref.value === 'cpu' ? 'cpu' : 'webgpu')
    void setPref(current === 'webgpu' ? 'cpu' : 'webgpu')
  }

  return { backend, webgpuAvailable, pref, switching, noteBackend, setPref, toggle }
}
