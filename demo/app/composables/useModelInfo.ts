import { getModelInfo } from '~/lib/agent/engine'

// Configured model repo/version/quant, the served file's hash (a cheap HEAD request, no download),
// and the size actually sitting in the OPFS cache - fetched once and shared across every consumer,
// mirroring useModelPreload.

export interface ModelInfo {
  repo: string
  version: string
  quant: string
  url: string
  sha256: string | null
  bytes: number | null
  diskBytes: number | null
}

const info = ref<ModelInfo | null>(null)
const errorMessage = ref<string | null>(null)
let checked = false

export function useModelInfo() {
  async function refresh() {
    if (!import.meta.client) return
    checked = true
    try {
      info.value = await getModelInfo()
      errorMessage.value = null
    } catch (err) {
      errorMessage.value = 'Could not check the model file.'
      console.error('[model-info] failed:', err)
    }
  }

  /** Mount hook - only fetches once; call `refresh()` after an action that changes the cache. */
  async function check() {
    if (checked) return
    await refresh()
  }

  return { info, errorMessage, check, refresh }
}
