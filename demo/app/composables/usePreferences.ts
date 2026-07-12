// Shared TTS/STT enabled state, module-level singletons so a preference set on the root picker
// page carries into whichever domain's agent panel/dialogue is opened next.

export const ttsEnabled = ref(false)
export const sttEnabled = ref(false)

export function usePreferences() {
  return { ttsEnabled, sttEnabled }
}
