// Shared runtime limits for the on-device agent. Centralized so context caps and budgeting
// stay consistent across the engine and the agent loop.

export const N_CTX = 8192 // wllama context window
export const MAX_OUTPUT_TOKENS = 320 // max tokens generated per assistant turn

// Warn if the injected system prompt (persona + catalog + tool list) exceeds this fraction of
// the context window - a signal that a growing catalog/KB is crowding out room for the
// conversation. Configurable.
export const SYSTEM_CTX_WARN_FRACTION = 0.15

// Token budget for accumulated conversation history (everything after the system prompt). Leaves
// room for the system prompt (up to the warn fraction), one full answer, and a safety margin, so
// the assembled prompt never overflows N_CTX - on overflow llama.cpp drops tokens from the FRONT,
// which is the catalog the model grounds slugs on.
export const HISTORY_TOKEN_BUDGET =
  N_CTX - Math.ceil(N_CTX * SYSTEM_CTX_WARN_FRACTION) - MAX_OUTPUT_TOKENS - 256

// Rough token estimate (~chars/4) - good enough for history budgeting without a tokenizer.
export const estimateTokens = (text: string | undefined): number => Math.ceil((text?.length ?? 0) / 4)
