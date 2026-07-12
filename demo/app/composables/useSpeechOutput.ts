// Optional TTS layer for the assistant: speaks new assistant replies via an in-browser neural TTS
// model (see ttsClient.ts) - the whisper-style counterpart to STT, and more reliable than the
// browser's built-in SpeechSynthesis (notably silent on Firefox/Linux without an OS voice backend).
// `enabled` is the shared preference (see usePreferences), so a toggle on the root picker page
// carries into whichever domain's panel opens next. State is a module-level singleton so it stays
// in sync wherever a panel/dialogue mounts.

import { ttsEnabled as enabled } from './usePreferences'

export type VoiceStatus = 'idle' | 'loading' | 'speaking' | 'error'

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

export function useSpeechOutput() {
  const supported = import.meta.client

  function enable() {
    enabled.value = true
    errorMessage.value = null
    if (status.value === 'error') status.value = 'idle'
    // Warm the model in the background so the first reply doesn't stall on a cold load.
    import('~/lib/agent/speech/ttsClient').then((m) => m.preloadTTS(state)).catch(() => {})
  }

  function disable() {
    enabled.value = false
  }

  function toggleEnabled() {
    if (enabled.value) disable()
    else enable()
  }

  /** Speak `text` if TTS is enabled. No-op otherwise (called unconditionally by callers). */
  async function speak(text: string) {
    if (!enabled.value || !supported || !text) return
    status.value = 'loading'
    try {
      const { speak: speakImpl } = await import('~/lib/agent/speech/ttsClient')
      status.value = 'speaking'
      await speakImpl(text, state)
      status.value = 'idle'
    } catch (err) {
      status.value = 'error'
      errorMessage.value = 'Speech playback failed - try Chrome/Edge, or disable voice replies.'
      console.error('[speech] tts failed:', err)
    }
  }

  return { supported, enabled, status, backend, modelProgress, errorMessage, enable, disable, toggleEnabled, speak }
}
