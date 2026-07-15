// Optional TTS layer: speaks new assistant replies via an in-browser neural TTS model (ttsClient),
// the counterpart to STT. `enabled` is the shared preference; state is a module-level singleton so
// it stays in sync wherever a panel mounts.

import { ttsEnabled as enabled } from './usePreferences'

export type VoiceStatus = 'idle' | 'loading' | 'speaking' | 'paused' | 'error'

export interface VoiceState {
  status: Ref<VoiceStatus>
  backend: Ref<'webgpu' | 'wasm' | null>
  modelProgress: Ref<number | null>
  errorMessage: Ref<string | null>
}

const status = ref<VoiceStatus>('idle')
const backend = ref<'webgpu' | 'wasm' | null>(null)
const modelProgress = ref<number | null>(null)
const errorMessage = ref<string | null>(null)
const state: VoiceState = { status, backend, modelProgress, errorMessage }

// Which transcript entry is loading/speaking/paused, so the UI can show controls on that bubble.
const speakingIndex = ref<number | null>(null)

// Bumped by every speak()/stop(). Only one track plays at a time; a superseded speak()'s
// continuation checks this before touching status/speakingIndex, so it can't clobber newer state.
let generation = 0

export function useSpeechOutput() {
  const supported = import.meta.client

  function enable() {
    enabled.value = true
    errorMessage.value = null
    if (status.value === 'error') status.value = 'idle'
    // Warm the model so the first reply doesn't stall on a cold load.
    import('~/lib/agent/speech/ttsClient').then((m) => m.preloadTTS(state)).catch(() => {})
  }

  function disable() {
    enabled.value = false
    void stop()
  }

  function toggleEnabled() {
    if (enabled.value) disable()
    else enable()
  }

  // Speak `text` if enabled. `index` identifies the owning transcript bubble for `speakingIndex`.
  async function speak(text: string, index?: number) {
    if (!enabled.value || !supported || !text) return
    const gen = ++generation
    status.value = 'loading'
    speakingIndex.value = index ?? null
    try {
      const { speak: speakImpl } = await import('~/lib/agent/speech/ttsClient')
      if (gen !== generation) return // superseded while the module was loading
      status.value = 'speaking'
      await speakImpl(text, state)
      if (gen !== generation) return // superseded while synthesizing/playing
      if (status.value !== 'error') status.value = 'idle'
      speakingIndex.value = null
    } catch (err) {
      if (gen !== generation) return
      status.value = 'error'
      speakingIndex.value = null
      errorMessage.value = 'Speech playback failed - try Chrome/Edge, or disable voice replies.'
      console.error('[speech] tts failed:', err)
    }
  }

  async function pause() {
    if (status.value !== 'speaking') return
    const { pause: pauseImpl } = await import('~/lib/agent/speech/ttsClient')
    pauseImpl()
    status.value = 'paused'
  }

  async function resume() {
    if (status.value !== 'paused') return
    const { resume: resumeImpl } = await import('~/lib/agent/speech/ttsClient')
    resumeImpl()
    status.value = 'speaking'
  }

  async function stop() {
    if (status.value !== 'speaking' && status.value !== 'paused') return
    generation++ // mark any in-flight speak() as superseded
    const { stop: stopImpl } = await import('~/lib/agent/speech/ttsClient')
    stopImpl()
    status.value = 'idle'
    speakingIndex.value = null
  }

  return {
    supported,
    enabled,
    status,
    modelProgress,
    errorMessage,
    speakingIndex,
    enable,
    disable,
    toggleEnabled,
    speak,
    pause,
    resume,
    stop,
  }
}
