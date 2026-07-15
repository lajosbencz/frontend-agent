import { useAgentStore } from '~/stores/agent'
import { domainSessions, type DomainKey } from '~/lib/agent/domains'

// Thin wrapper over the library Session (which owns history, the tool loop, and GBNF/id-grounding):
// feed user text in via send(); its event stream updates the store, wired per domain.

export function useAgentLoop(domain: DomainKey) {
  const agent = useAgentStore(domain)
  const session = domainSessions[domain]

  async function send(userText: string) {
    agent.pushUser(userText)
    const s = await session.getSession()
    await s.submit(userText)
  }

  async function stop() {
    const s = await session.getSession()
    s.abort()
  }

  return { send, stop }
}
