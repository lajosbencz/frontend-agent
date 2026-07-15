// In-browser text-to-speech via transformers.js / ONNX Runtime Web - the mirror of whisperClient's
// STT. Browser SpeechSynthesis is unreliable cross-platform (notably silent on Firefox/Linux without
// an OS speech backend), so replies are synthesized with an on-device model. Dynamically imported.

import type { VoiceState } from '~/composables/useSpeechOutput'
import { detectWebGPU } from './webgpu'

// Lightweight single-speaker English VITS model - small download, no GPU required.
const MODEL_ID = 'Xenova/mms-tts-eng'

interface SynthesisResult {
  audio: Float32Array
  sampling_rate: number
}
type Synthesizer = (text: string) => Promise<SynthesisResult>

let pipePromise: Promise<Synthesizer> | null = null
let audioCtx: AudioContext | null = null

async function getSynthesizer(state: VoiceState): Promise<Synthesizer> {
  if (pipePromise) return pipePromise
  pipePromise = (async () => {
    const { pipeline, env } = await import('@huggingface/transformers')
    env.allowLocalModels = false

    const useGPU = await detectWebGPU()
    state.backend.value = useGPU ? 'webgpu' : 'wasm'

    const synthesizer = (await pipeline('text-to-speech', MODEL_ID, {
      device: useGPU ? 'webgpu' : 'wasm',
      dtype: useGPU ? 'fp32' : 'q8',
      progress_callback: (p: { status?: string; progress?: number }) => {
        if (p.status === 'progress' && typeof p.progress === 'number') {
          state.modelProgress.value = Math.round(p.progress)
        } else if (p.status === 'ready') {
          state.modelProgress.value = 100
        }
      },
    })) as unknown as Synthesizer
    return synthesizer
  })()
  return pipePromise
}

let activeSource: AudioBufferSourceNode | null = null
let activeResolve: (() => void) | null = null

// Pause/resume suspend the whole AudioContext clock - an AudioBufferSourceNode can't be paused.
export function pause(): void {
  void audioCtx?.suspend()
}

export function resume(): void {
  void audioCtx?.resume()
}

// Stop the current utterance and resolve its speak() immediately - the node's `ended` event may
// never fire while the context is suspended (paused).
export function stop(): void {
  if (!activeSource) return
  const source = activeSource
  const resolveDone = activeResolve
  activeSource = null
  activeResolve = null
  source.onended = null
  try {
    source.stop()
  } catch {
    /* already stopped */
  }
  resolveDone?.()
  void audioCtx?.resume()
}

function playAudio(audio: Float32Array, samplingRate: number): Promise<void> {
  audioCtx ??= new AudioContext()
  const buffer = audioCtx.createBuffer(1, audio.length, samplingRate)
  buffer.copyToChannel(audio, 0)
  const source = audioCtx.createBufferSource()
  source.buffer = buffer
  source.connect(audioCtx.destination)
  activeSource = source
  return new Promise((resolve) => {
    activeResolve = resolve
    source.onended = () => {
      if (activeSource === source) {
        activeSource = null
        activeResolve = null
      }
      resolve()
    }
    source.start()
  })
}

// Synthesize and play `text`; only one track plays at once, so stop whatever's active first.
export async function speak(text: string, state: VoiceState): Promise<void> {
  stop()
  const synthesizer = await getSynthesizer(state)
  const { audio, sampling_rate } = await synthesizer(text)
  await playAudio(audio, sampling_rate)
}

export function preloadTTS(state: VoiceState): void {
  void getSynthesizer(state).catch(() => {})
}
