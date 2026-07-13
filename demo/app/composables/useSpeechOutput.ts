// Optional TTS layer for the assistant: speaks new assistant replies via an in-browser neural TTS
// model (see ttsClient.ts) - the whisper-style counterpart to STT, and more reliable than the
// browser's built-in SpeechSynthesis (notably silent on Firefox/Linux without an OS voice backend).
// `enabled` is the shared preference (see usePreferences), so a toggle on the root picker page
// carries into whichever domain's panel opens next. State is a module-level singleton so it stays
// in sync wherever a panel/dialogue mounts.

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

/** Which transcript entry (by index, caller-defined) is currently loading/speaking/paused, if any -
 *  lets the transcript show play/pause/stop controls next to that specific message bubble. */
const speakingIndex = ref<number | null>(null)

// Bumped by every speak()/stop() call. Only one track plays at a time (ttsClient.speak() stops
// whatever's active first) - a superseded speak() call's continuation checks this before touching
// status/speakingIndex, so it can't clobber the newer call's state once the older track is stopped.
let generation = 0

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
    void stop()
  }

  function toggleEnabled() {
    if (enabled.value) disable()
    else enable()
  }

  /** Speak `text` if TTS is enabled. No-op otherwise (called unconditionally by callers). `index`
   *  identifies the transcript entry for `speakingIndex`, so the UI knows which bubble owns this. */
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

  /** Pause the in-flight utterance (no-op if nothing is speaking). */
  async function pause() {
    if (status.value !== 'speaking') return
    const { pause: pauseImpl } = await import('~/lib/agent/speech/ttsClient')
    pauseImpl()
    status.value = 'paused'
  }

  /** Resume a paused utterance. */
  async function resume() {
    if (status.value !== 'paused') return
    const { resume: resumeImpl } = await import('~/lib/agent/speech/ttsClient')
    resumeImpl()
    status.value = 'speaking'
  }

  /** Stop the in-flight/paused utterance outright. Leaves `speakingIndex` alone if nothing was
   *  playing, so a stray call (e.g. from `disable()`) can't disturb an already-idle state. */
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
    backend,
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
