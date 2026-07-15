import { Wllama, type AssetsPathConfig } from '@wllama/wllama'
import { parseToolCalls } from '../parsing/toolCallParser'
import { renderToolCalls } from '../parsing/renderToolCalls'
import { N_CTX, MAX_OUTPUT_TOKENS, SYSTEM_CTX_WARN_FRACTION, estimateTokens } from '../limits'
import type { AgentEngine, ChatMessage, EngineGenerateResult } from './types'

/** Reference to a GGUF published on the Hugging Face Hub. */
export interface HFModelRef {
  repo?: string
  version?: string
  quant?: string
}

export type EngineStatus = 'idle' | 'downloading' | 'loading' | 'ready'

export interface WllamaEngineConfig {
  /** Load the GGUF from Hugging Face (default). Ignored if `modelUrl` is set. */
  model?: HFModelRef
  /** Full GGUF URL - self-host escape hatch; overrides `model`. */
  modelUrl?: string
  /** wllama WASM asset config, e.g. `{ 'single-thread/wllama.wasm': url, 'multi-thread/wllama.wasm': url }`. */
  wllamaAssets: AssetsPathConfig
  /** Context window. Default 8192. */
  nCtx?: number
  /** Max tokens per assistant turn. Default 320. */
  maxTokens?: number
  /** Backend preference. `'auto'` uses WebGPU when a real adapter is present. Default `'auto'`. */
  backend?: 'auto' | 'webgpu' | 'cpu'
  onStatus?: (status: EngineStatus) => void
  onProgress?: (progress: { loaded: number; total: number }) => void
  /** Reports whether a usable WebGPU adapter was detected (after load). */
  onBackend?: (info: { webgpu: boolean; using: 'webgpu' | 'cpu' }) => void
}

const DEFAULT_MODEL: Required<HFModelRef> = {
  repo: 'lazos/lfm2.5-230m-frontend-agent',
  version: 'main',
  quant: 'Q4_K_M',
}

/** Fill in any missing fields of a model ref from the library default. */
export function resolveModelRef(ref: HFModelRef = {}): Required<HFModelRef> {
  return { ...DEFAULT_MODEL, ...ref }
}

/** Resolve a HF model ref to its GGUF URL: `resolve/{version}/{basename}-{quant}.gguf`. */
export function resolveModelUrl(ref: HFModelRef = {}): string {
  const { repo, version, quant } = resolveModelRef(ref)
  const basename = repo.split('/').pop() ?? repo
  return `https://huggingface.co/${repo}/resolve/${version}/${basename}-${quant}.gguf`
}

export interface ModelFileMeta {
  /** Content hash from the response ETag (sha256 for HF's LFS/Xet-backed files), quotes stripped. */
  sha256: string | null
  bytes: number | null
}

/** HEAD the GGUF URL for its content hash + size without downloading. For a floating ref (`main`)
 *  the hash is the only reliable identity of the build actually served. */
export async function fetchModelMeta(url: string): Promise<ModelFileMeta> {
  const res = await fetch(url, { method: 'HEAD' })
  const etag = res.headers.get('etag')
  return {
    sha256: etag ? etag.replace(/^"|"$/g, '') : null,
    bytes: Number(res.headers.get('content-length')) || null,
  }
}

async function detectWebGPU(): Promise<boolean> {
  try {
    const gpu = (navigator as unknown as { gpu?: { requestAdapter?: () => Promise<unknown> } }).gpu
    if (!gpu?.requestAdapter) return false
    return (await gpu.requestAdapter()) != null
  } catch {
    return false
  }
}

/** Runs the GGUF in-browser via wllama (llama.cpp WASM/WebGPU): loads from HF (OPFS-cached), applies
 *  the GBNF grammar at decode. Framework-agnostic - lifecycle via callbacks, no store coupling. */
export class WllamaEngine implements AgentEngine {
  private wllamaPromise: Promise<Wllama> | null = null
  private warnedSystemSize = false
  private readonly url: string
  private readonly nCtx: number
  private readonly maxTokens: number

  constructor(private readonly config: WllamaEngineConfig) {
    this.url = config.modelUrl ?? resolveModelUrl(config.model)
    this.nCtx = config.nCtx ?? N_CTX
    this.maxTokens = config.maxTokens ?? MAX_OUTPUT_TOKENS
  }

  async load(): Promise<void> {
    await this.getWllama()
  }

  /** Tear down the loaded model so it can be reloaded (e.g. on a backend switch). OPFS-cached. */
  async reset(): Promise<void> {
    const p = this.wllamaPromise
    this.wllamaPromise = null
    try {
      const inst = p ? await p : null
      await (inst as unknown as { exit?: () => Promise<void> })?.exit?.()
    } catch {
      /* ignore teardown errors */
    }
  }

  private getWllama(): Promise<Wllama> {
    if (this.wllamaPromise) return this.wllamaPromise
    this.wllamaPromise = (async () => {
      const { onStatus, onProgress, onBackend, backend = 'auto', wllamaAssets } = this.config
      const hasWebGPU = await detectWebGPU()
      const useGPU = hasWebGPU && backend !== 'cpu'
      onBackend?.({ webgpu: hasWebGPU, using: useGPU ? 'webgpu' : 'cpu' })

      const load = async (nThreads?: number): Promise<Wllama> => {
        const instance = new Wllama(wllamaAssets)
        onStatus?.('downloading')
        // wllama has no "download done, initializing" hook; progress pinned at 100% before
        // loadModelFromUrl resolves IS that gap - infer the loading transition from it (once).
        let announcedLoading = false
        await instance.loadModelFromUrl(this.url, {
          n_ctx: this.nCtx,
          n_gpu_layers: useGPU ? 99999 : 0,
          ...(nThreads ? { n_threads: nThreads } : {}),
          progressCallback: ({ loaded, total }) => {
            onProgress?.({ loaded, total })
            if (!announcedLoading && total > 0 && loaded >= total) {
              announcedLoading = true
              onStatus?.('loading')
            }
          },
        })
        return instance
      }

      // Fast path (WebGPU / multi-thread WASM); on a threads-build trap fall back once to
      // single-thread. Reacts to the real failure, not a UA string. OPFS-cached so no re-download.
      let instance: Wllama
      try {
        instance = await load()
      } catch (err) {
        console.warn('[frontend-agent] multi-thread load failed; retrying single-thread:', err)
        instance = await load(1)
      }
      onStatus?.('ready')
      return instance
    })()
    return this.wllamaPromise
  }

  async generate(messages: ChatMessage[], grammar?: string): Promise<EngineGenerateResult> {
    const wllama = await this.getWllama()

    if (!this.warnedSystemSize) {
      const sys = messages.find((m) => m.role === 'system')?.content ?? ''
      const tokenize = (wllama as { tokenize?: (s: string) => Promise<number[]> }).tokenize
      let sysTokens: number
      try {
        sysTokens = tokenize ? (await tokenize.call(wllama, sys)).length : estimateTokens(sys)
      } catch {
        sysTokens = estimateTokens(sys)
      }
      if (sysTokens > this.nCtx * SYSTEM_CTX_WARN_FRACTION) {
        this.warnedSystemSize = true
        console.warn(
          `[frontend-agent] system prompt is ${sysTokens} tokens - over ` +
            `${Math.round(SYSTEM_CTX_WARN_FRACTION * 100)}% of the ${this.nCtx}-token context. ` +
            'A larger catalog/KB is crowding out the conversation; trim the injected catalog or raise nCtx.',
        )
      }
    }

    // Tools live in the system text already, so pass NO `tools`; the GBNF grammar (when supplied)
    // guarantees a structurally-valid call + id-grounding at decode time.
    const response = await wllama.createChatCompletion({
      messages: messages as never,
      max_tokens: this.maxTokens,
      temperature: 0,
      ...(grammar ? { grammar } : {}),
    } as never)
    const message = (response as { choices: { message: WllamaMessage }[] }).choices[0]!.message

    if (message.tool_calls && message.tool_calls.length > 0) {
      const toolCalls = message.tool_calls.map((c) => ({
        name: c.function.name,
        args: safeJson(c.function.arguments),
      }))
      return { text: message.content ?? '', toolCalls, raw: renderToolCalls(toolCalls) }
    }

    const rawContent = message.content ?? ''
    const parsed = parseToolCalls(rawContent)
    return { text: parsed.text, toolCalls: parsed.toolCalls, raw: rawContent }
  }
}

interface WllamaMessage {
  content?: string
  tool_calls?: { function: { name: string; arguments: string } }[]
}

function safeJson(s: string): Record<string, unknown> {
  try {
    return JSON.parse(s || '{}')
  } catch {
    return {}
  }
}
