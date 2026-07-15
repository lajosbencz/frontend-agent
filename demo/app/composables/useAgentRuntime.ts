import { useAgentStore } from '~/stores/agent'
import { getEngine } from '~/lib/agent/engine'
import { useBackend, type BackendPref } from '~/composables/useBackend'
import { domainSessions, type DomainKey } from '~/lib/agent/domains'

// Owns the activation UX (download/progress) for a domain's Session; GPU/CPU preference lives in
// useBackend.

export function useAgentRuntime(domain: DomainKey) {
  const agent = useAgentStore(domain)
  const session = domainSessions[domain]
  const backend = useBackend()

  async function activate() {
    if (agent.status !== 'idle') {
      agent.panelOpen = true
      return
    }
    agent.panelOpen = true
    agent.status = 'checking-cache'
    try {
      await getEngine({
        onStatus: (s) => {
          if (s === 'downloading') agent.status = 'downloading'
          else if (s === 'loading') agent.status = 'loading-into-memory'
          else if (s === 'ready' && agent.status !== 'thinking') agent.status = 'ready'
        },
        onProgress: ({ loaded, total }) => {
          agent.downloadProgress = { bytesLoaded: loaded, bytesTotal: total }
        },
        onBackend: backend.noteBackend,
      })
      if (agent.status !== 'thinking') agent.status = 'ready'
    } catch (err) {
      agent.status = 'error'
      agent.errorMessage =
        "The assistant couldn't start in this browser (a WebAssembly compatibility issue). " +
        'Chrome or Edge are the best-supported browsers - please try one of those.'
      console.error(`[${domain}] engine load failed:`, err)
    }
  }

  /** Switch inference backend (GPU/CPU) and reload the model on it (OPFS-cached, no re-download). */
  async function switchBackend(pref: BackendPref) {
    if (agent.status === 'thinking' || agent.status === 'downloading') return
    agent.status = 'checking-cache'
    try {
      await backend.setPref(pref)
      session.resetSession()
      agent.status = 'ready'
    } catch (err) {
      agent.status = 'error'
      agent.errorMessage = 'Failed to switch backend - try the other one, or Chrome/Edge.'
      console.error(`[${domain}] backend switch failed:`, err)
    }
  }

  return { activate, switchBackend }
}
