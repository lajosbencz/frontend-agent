// Shared TTS/STT enabled state (module-level singletons) so a preference set on the picker page
// carries into whichever domain's agent panel opens next.

export const ttsEnabled = ref(false)
export const sttEnabled = ref(false)
