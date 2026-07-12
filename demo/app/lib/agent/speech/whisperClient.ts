// Optional in-browser speech-to-text (Whisper-tiny) via transformers.js / ONNX Runtime Web.
// Mirrors the wllama engine's philosophy: nothing runs server-side, weights are fetched once
// and cached by the browser (Cache API), and the backend (WebGPU/WASM) is picked at runtime.
// The whole module is dynamically imported so its ~40MB of model weights + ORT wasm never
// touch the main bundle - it loads only when the user first taps the mic.

import type { SpeechState } from '~/composables/useSpeechInput'

// English-only tiny model: smallest reliable option for this English shop, faster and more
// accurate on en than the multilingual tiny. Bump/replace to switch languages.
const MODEL_ID = 'Xenova/whisper-tiny.en'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Transcriber = (audio: Float32Array, opts?: Record<string, unknown>) => Promise<any>

let pipePromise: Promise<Transcriber> | null = null

async function detectWebGPU(): Promise<boolean> {
  try {
    const gpu = (navigator as unknown as { gpu?: { requestAdapter?: () => Promise<unknown> } }).gpu
    if (!gpu?.requestAdapter) return false
    return (await gpu.requestAdapter()) != null
  } catch {
    return false
  }
}

/** Build (once) the ASR pipeline, wiring model-download progress into the shared speech state. */
async function getTranscriber(state: SpeechState): Promise<Transcriber> {
  if (pipePromise) return pipePromise
  pipePromise = (async () => {
    const { pipeline, env } = await import('@huggingface/transformers')
    // Fetch weights from the HF hub CDN; no local model dir. Cache API keeps them across reloads.
    env.allowLocalModels = false

    const useGPU = await detectWebGPU()
    state.backend.value = useGPU ? 'webgpu' : 'wasm'

    const transcriber = (await pipeline('automatic-speech-recognition', MODEL_ID, {
      device: useGPU ? 'webgpu' : 'wasm',
      // fp32 on GPU (whisper-tiny is small); quantized int8 on CPU/WASM for speed + smaller download.
      dtype: useGPU ? 'fp32' : 'q8',
      progress_callback: (p: { status?: string; progress?: number }) => {
        if (p.status === 'progress' && typeof p.progress === 'number') {
          state.modelProgress.value = Math.round(p.progress)
        } else if (p.status === 'ready') {
          state.modelProgress.value = 100
        }
      },
    })) as unknown as Transcriber
    return transcriber
  })()
  return pipePromise
}

/** Transcribe mono 16kHz PCM to text. Loads the model on first call (progress via `state`). */
export async function transcribe(audio: Float32Array, state: SpeechState): Promise<string> {
  const transcriber = await getTranscriber(state)
  const out = await transcriber(audio)
  const text = Array.isArray(out) ? out.map((o) => o.text).join(' ') : (out?.text ?? '')
  return String(text).trim()
}

/** Kick off model loading without transcribing, so it's warm by the time recording stops. */
export function preloadWhisper(state: SpeechState): void {
  void getTranscriber(state).catch(() => {
    /* surfaced when transcribe() is actually awaited */
  })
}
