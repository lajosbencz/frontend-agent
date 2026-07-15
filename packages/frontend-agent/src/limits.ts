// Shared runtime limits, centralized so engine and agent loop stay consistent.

export const N_CTX = 8192 // wllama context window
export const MAX_OUTPUT_TOKENS = 320 // max tokens per assistant turn

/** Warn when the system prompt exceeds this fraction of the context window (catalog/KB crowding out
 *  the conversation). */
export const SYSTEM_CTX_WARN_FRACTION = 0.15

// Budget for history after the system prompt. On overflow llama.cpp drops tokens from the FRONT
// (the catalog the model grounds on), so keep the assembled prompt under N_CTX.
export const HISTORY_TOKEN_BUDGET =
  N_CTX - Math.ceil(N_CTX * SYSTEM_CTX_WARN_FRACTION) - MAX_OUTPUT_TOKENS - 256

/** Rough token estimate (~chars/4); good enough for history budgeting without a tokenizer. */
export const estimateTokens = (text: string | undefined): number => Math.ceil((text?.length ?? 0) / 4)
