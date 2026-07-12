import { useAgentStore } from '~/stores/agent'
import { domainSessions, type DomainKey } from '~/lib/agent/domains'

// Thin Vue wrapper over the library Session. The Session owns the model-format history, the tool
// loop, and the GBNF/id-grounding; here we just feed user text in and let its event stream update
// the store (wired in each domain module). `submit(text)` is the single entry point - typed input
// and STT both call it.

export function useAgentLoop(domain: DomainKey) {
  const agent = useAgentStore(domain)
  const session = domainSessions[domain]

  async function send(userText: string) {
    agent.pushUser(userText)
    const s = await session.getSession()
    await s.submit(userText)
  }

  /** Stop the in-flight turn. */
  async function stop() {
    const s = await session.getSession()
    s.abort()
  }

  return { send, stop }
}
