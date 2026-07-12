import { defineStore } from 'pinia'

export type AgentStatus =
  | 'idle'
  | 'checking-cache'
  | 'downloading'
  | 'loading-into-memory'
  | 'ready'
  | 'thinking'
  | 'error'

export interface DownloadProgress {
  bytesLoaded: number
  bytesTotal: number
}

export interface ToolCallRecord {
  name: string
  args: Record<string, unknown>
  result?: unknown
  done: boolean
}

export interface TranscriptEntry {
  role: 'user' | 'assistant'
  content: string
  tools?: ToolCallRecord[]
}

const stores = new Map<string, ReturnType<typeof defineAgentStore>>()

// UI state only. The model-format conversation lives inside the library Session (runtime.ts);
// this store just drives the panel: transcript, load status, download progress. GPU/CPU backend
// state lives in useBackend (shared across domains). One instance per domain (brewcraft/emporium/
// vendor), so conversations never mix across demos.
function defineAgentStore(domain: string) {
  return defineStore(`agent:${domain}`, {
    state: () => ({
      status: 'idle' as AgentStatus,
      panelOpen: false,
      transcript: [] as TranscriptEntry[],
      downloadProgress: null as DownloadProgress | null,
      errorMessage: null as string | null,
      pendingTools: [] as ToolCallRecord[],
    }),
    actions: {
      pushUser(content: string) {
        this.transcript.push({ role: 'user', content })
      },
      pushAssistant(content: string) {
        const tools = this.pendingTools.length ? this.pendingTools : undefined
        this.pendingTools = []
        if (content || tools) this.transcript.push({ role: 'assistant', content, tools })
      },
      pushToolCallNotice(call: { name: string; args: Record<string, unknown> }) {
        this.pendingTools.push({ name: call.name, args: call.args, done: false })
      },
      pushToolResult(name: string, result: unknown) {
        const rec = [...this.pendingTools].reverse().find((t) => t.name === name && !t.done)
        if (rec) {
          rec.result = result
          rec.done = true
        }
      },
      reset() {
        this.transcript = []
        this.pendingTools = []
      },
    },
  })
}

export function useAgentStore(domain: string) {
  let define = stores.get(domain)
  if (!define) {
    define = defineAgentStore(domain)
    stores.set(domain, define)
  }
  return define()
}
