import { getModelInfo } from '~/lib/agent/engine'

// Configured model repo/version/quant, the served file's hash (cheap HEAD, no download), and the
// size sitting in the OPFS cache - fetched once and shared across every consumer.

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
let checked = false

export function useModelInfo() {
  async function refresh() {
    if (!import.meta.client) return
    checked = true
    try {
      info.value = await getModelInfo()
    } catch (err) {
      console.error('[model-info] failed:', err)
    }
  }

  // Mount hook - fetches once; call refresh() after an action that changes the cache.
  async function check() {
    if (checked) return
    await refresh()
  }

  return { info, check, refresh }
}
