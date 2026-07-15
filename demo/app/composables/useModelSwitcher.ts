import {
  FRONTEND_AGENT_MODELS,
  DEFAULT_MODEL_ID,
  modelOptionById,
  modelOptionForRef,
  type ModelOption,
  type HFModelRef,
} from 'frontend-agent'
import { resetEngine, setModelOverride } from '~/lib/agent/engine'
import { useModelPreload } from '~/composables/useModelPreload'

// Module-level singleton so the selector drives one shared selection everywhere. A pick is
// (size+quant = catalog id) + a version (HF git tag). Selecting rebuilds the engine on the next load.

const STORAGE_KEY = 'fa:model-id'
const VERSION_KEY = 'fa:model-version'
const RECOMMENDED = modelOptionById(DEFAULT_MODEL_ID) // smallest 230M on `main`

const currentId = ref<string>(DEFAULT_MODEL_ID)
const currentVersion = ref<string>(modelOptionById(DEFAULT_MODEL_ID).ref.version)
const switching = ref(false)
const errorMessage = ref<string | null>(null)
const versions = ref<string[]>([]) // ['main', <tags newest-first>], fetched from the HF repo
let initialized = false

function refFor(id: string, version: string): HFModelRef {
  return { ...modelOptionById(id).ref, version }
}

export function useModelSwitcher() {
  /** A self-host `modelUrl` is configured: engine serves it directly, roster is hidden. */
  const selfHosted = computed(() => !!useRuntimeConfig().public.modelUrl)

  /** Apply the persisted pick (as an override so the first load uses it), else the build-time config. */
  function init() {
    if (initialized || !import.meta.client) return
    initialized = true
    const cfg = useRuntimeConfig().public
    if (cfg.modelUrl) return // self-host: engine serves modelUrl, no override

    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && FRONTEND_AGENT_MODELS.some((m) => m.id === saved)) {
      currentId.value = saved
      currentVersion.value = localStorage.getItem(VERSION_KEY) || modelOptionById(saved).ref.version
      setModelOverride(refFor(saved, currentVersion.value))
      return
    }
    const cfgRef: HFModelRef = {}
    if (cfg.modelRepo) cfgRef.repo = cfg.modelRepo
    if (cfg.modelVersion) cfgRef.version = cfg.modelVersion
    if (cfg.modelQuant) cfgRef.quant = cfg.modelQuant
    const opt = modelOptionForRef(cfgRef)
    if (opt) currentId.value = opt.id
    if (cfg.modelVersion) currentVersion.value = cfg.modelVersion
  }

  /** Fetch the HF repo's version tags (newest first, `main` on top). Falls back to the current version. */
  async function loadVersions(): Promise<void> {
    if (versions.value.length) return
    const repo = modelOptionById(currentId.value).ref.repo
    try {
      const res = await fetch(`https://huggingface.co/api/models/${repo}/refs`)
      if (!res.ok) throw new Error(String(res.status))
      const data = (await res.json()) as { tags?: { name: string }[] }
      const tags = (data.tags ?? [])
        .map((t) => t.name)
        .sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))
      versions.value = ['main', ...tags.filter((t) => t !== 'main')]
    } catch {
      versions.value = Array.from(new Set(['main', currentVersion.value]))
    }
  }

  const models = FRONTEND_AGENT_MODELS
  const current = computed<ModelOption>(() => modelOptionById(currentId.value))
  /** One-line status for the selector chrome (select is download-free, so just teardown/error). */
  const statusText = computed(() => (errorMessage.value ? errorMessage.value : switching.value ? 'Switching...' : ''))
  /** Whether the current pick is the catalog default (the recommended build + `main`). */
  const isRecommended = computed(
    () => currentId.value === RECOMMENDED.id && currentVersion.value === RECOMMENDED.ref.version,
  )
  const resetToRecommended = () => select(RECOMMENDED.id, RECOMMENDED.ref.version)

  /** Select a build WITHOUT downloading: record the pick and tear down any resident engine so nothing
   *  stale answers. The load happens later (Preload button, or the next chat message). Reverts on failure. */
  async function select(id: string, version?: string): Promise<void> {
    const v = version ?? currentVersion.value
    if (switching.value) return
    if (id === currentId.value && v === currentVersion.value) return
    if (!FRONTEND_AGENT_MODELS.some((m) => m.id === id)) return
    const prevId = currentId.value
    const prevV = currentVersion.value
    switching.value = true
    errorMessage.value = null
    currentId.value = id
    currentVersion.value = v
    setModelOverride(refFor(id, v))
    try {
      await resetEngine() // drop the old model + invalidate every domain Session; do NOT reload
      localStorage.setItem(STORAGE_KEY, id)
      localStorage.setItem(VERSION_KEY, v)
      await useModelPreload().syncToSelection() // new pick not loaded yet; recheck its cache
    } catch (err) {
      currentId.value = prevId
      currentVersion.value = prevV
      setModelOverride(refFor(prevId, prevV))
      errorMessage.value = err instanceof Error ? `${err.name}: ${err.message}` : String(err)
      console.error('[model] select failed:', err)
    } finally {
      switching.value = false
    }
  }

  return {
    models, current, currentId, currentVersion, versions, switching, errorMessage, statusText,
    selfHosted, isRecommended, init, loadVersions, select, resetToRecommended,
  }
}
