// In-browser speech-to-text (Whisper-tiny) via transformers.js / ONNX Runtime Web. Nothing runs
// server-side; weights are fetched once and cached by the browser, backend picked at runtime.
// Dynamically imported so its ~40MB of weights + ORT wasm never touch the main bundle.

import type { SpeechState } from '~/composables/useSpeechInput'
import { detectWebGPU } from './webgpu'

// English-only tiny model: smallest reliable option, faster/more accurate on en than multilingual.
const MODEL_ID = 'Xenova/whisper-tiny.en'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Transcriber = (audio: Float32Array, opts?: Record<string, unknown>) => Promise<any>

let pipePromise: Promise<Transcriber> | null = null

async function getTranscriber(state: SpeechState): Promise<Transcriber> {
  if (pipePromise) return pipePromise
  pipePromise = (async () => {
    const { pipeline, env } = await import('@huggingface/transformers')
    env.allowLocalModels = false

    const useGPU = await detectWebGPU()
    state.backend.value = useGPU ? 'webgpu' : 'wasm'

    const transcriber = (await pipeline('automatic-speech-recognition', MODEL_ID, {
      device: useGPU ? 'webgpu' : 'wasm',
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

export async function transcribe(audio: Float32Array, state: SpeechState): Promise<string> {
  const transcriber = await getTranscriber(state)
  const out = await transcriber(audio)
  const text = Array.isArray(out) ? out.map((o) => o.text).join(' ') : (out?.text ?? '')
  return String(text).trim()
}

// Warm the model without transcribing, so it's ready by the time recording stops.
export function preloadWhisper(state: SpeechState): void {
  void getTranscriber(state).catch(() => {})
}
