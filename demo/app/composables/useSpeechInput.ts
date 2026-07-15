import { micSupported, startRecording, type Recording } from '~/lib/agent/speech/recorder'
import { sttEnabled as enabled } from './usePreferences'

// Optional voice layer: record -> Whisper-tiny -> text, fed into the normal send path. State is a
// module-level singleton so the mic button/status stay in sync wherever the panel mounts; the
// whisper module is imported lazily on first use.

export type SpeechStatus = 'idle' | 'recording' | 'transcribing' | 'error'
export type MicPermission = 'unknown' | 'granted' | 'denied'

export interface SpeechState {
  status: Ref<SpeechStatus>
  backend: Ref<'webgpu' | 'wasm' | null>
  modelProgress: Ref<number | null>
  errorMessage: Ref<string | null>
}

// Off by default; the user opts in via the panel toggle (which requests mic permission once).
const permission = ref<MicPermission>('unknown')
const status = ref<SpeechStatus>('idle')
const backend = ref<'webgpu' | 'wasm' | null>(null)
const modelProgress = ref<number | null>(null)
const errorMessage = ref<string | null>(null)
const state: SpeechState = { status, backend, modelProgress, errorMessage }

let recording: Recording | null = null

// Whisper hallucinates a stock word ("you", "Thank you.") on near-silent input rather than
// failing loudly - a wrong/muted OS input device still passes getUserMedia's permission check,
// so we can't tell from permission state alone. Catch it here instead of shipping nonsense text.
const SILENCE_PEAK_THRESHOLD = 0.01

function peakAmplitude(samples: Float32Array): number {
  let peak = 0
  for (let i = 0; i < samples.length; i++) {
    const a = Math.abs(samples[i])
    if (a > peak) peak = a
  }
  return peak
}

async function requestMicPermission(): Promise<boolean> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    stream.getTracks().forEach((t) => t.stop()) // only wanted the grant
    permission.value = 'granted'
    return true
  } catch (err) {
    permission.value = 'denied'
    console.error('[speech] mic permission denied:', err)
    return false
  }
}

export function useSpeechInput() {
  const supported = import.meta.client && micSupported()

  async function enable() {
    if (!supported) {
      status.value = 'error'
      errorMessage.value = 'Voice input needs a mic and a secure (https) context.'
      return
    }
    if (permission.value !== 'granted' && !(await requestMicPermission())) {
      status.value = 'error'
      errorMessage.value = 'Microphone permission was blocked - enable it in the browser to use voice.'
      return
    }
    errorMessage.value = null
    if (status.value === 'error') status.value = 'idle'
    enabled.value = true
  }

  function disable() {
    cancel()
    enabled.value = false
  }

  async function toggleEnabled() {
    if (enabled.value) disable()
    else await enable()
  }

  // One button for the whole cycle: returns the transcript when a take completes, or null when it
  // just started recording / errored. Model load runs in parallel with recording.
  async function toggle(): Promise<string | null> {
    if (!enabled.value) return null

    if (status.value === 'recording') {
      const rec = recording
      recording = null
      status.value = 'transcribing'
      try {
        const audio = await rec!.stop()
        if (audio.length === 0 || peakAmplitude(audio) < SILENCE_PEAK_THRESHOLD) {
          status.value = 'error'
          errorMessage.value =
            'No audio was picked up - check that the right microphone is selected (and not muted) in your browser/OS, then try again.'
          return null
        }
        const { transcribe } = await import('~/lib/agent/speech/whisperClient')
        const text = await transcribe(audio, state)
        status.value = 'idle'
        return text || null
      } catch (err) {
        status.value = 'error'
        errorMessage.value = 'Transcription failed - check mic permission, or try again.'
        console.error('[speech] transcription failed:', err)
        return null
      }
    }

    errorMessage.value = null
    try {
      // Warm the model while the user speaks.
      const { preloadWhisper } = await import('~/lib/agent/speech/whisperClient')
      preloadWhisper(state)
      recording = await startRecording()
      status.value = 'recording'
    } catch (err) {
      status.value = 'error'
      errorMessage.value = 'Could not access the microphone - check browser permissions.'
      console.error('[speech] mic start failed:', err)
    }
    return null
  }

  function cancel() {
    recording?.cancel()
    recording = null
    if (status.value === 'recording') status.value = 'idle'
  }

  return {
    supported,
    enabled,
    status,
    modelProgress,
    errorMessage,
    enable,
    disable,
    toggleEnabled,
    toggle,
  }
}
