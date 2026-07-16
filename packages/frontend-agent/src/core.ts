// `frontend-agent/core` - the pure primitives, with ZERO heavy deps. Importing from here never pulls
// @wllama/wllama (WASM/TS) or minisearch/stemmer, so a bring-your-own-engine consumer (or a stub)
// pays for none of it. The WllamaEngine lives behind `frontend-agent/wllama`; RAG behind `.../rag`.

export { createFrontendAgent } from './createFrontendAgent'
export type { FrontendAgentConfig, ViewSource, CartLineSource } from './createFrontendAgent'

export { createBoundedAgent } from './createBoundedAgent'
export type { BoundedAgentConfig } from './createBoundedAgent'

export { createAgent } from './loop/agent'
export type { Session, AgentConfig, AgentEvent, ToolCall, SubmitOptions } from './loop/agent'

export { StubEngine, makeStubEngine } from './engine/stubEngine'
export type { AgentEngine, ChatMessage, EngineGenerateResult } from './engine/types'

export { probeHardware, MIN_GFLOPS } from './engine/hardwareProbe'
export type { HardwareProbe } from './engine/hardwareProbe'

export { buildToolGrammar, collectIds } from './engine/gbnf'

export { buildSystemPrompt } from './prompt/systemPrompt'
export type { SystemPromptConfig } from './prompt/systemPrompt'

export { renderContext, CONTEXT_SCHEMA_VERSION, ContextManager } from './context'
export type {
  ContextInput,
  ViewItem,
  CartItem,
  KnowledgeSnippet,
  ContextManagerConfig,
} from './context'
export { assertPromptParity, PromptParityError } from './context'
export type { PromptParityCase, PromptParityFixtures } from './context'

export { pyJson } from './prompt/pyJson'

export { parseToolCalls } from './parsing/toolCallParser'
export type { ParsedToolCall, ParseResult } from './parsing/toolCallParser'
export { renderToolCalls } from './parsing/renderToolCalls'

export { buildRegistry } from './tools/registry'
export type { ToolRegistry } from './tools/registry'
export type { ToolSchema, ToolHandler, ToolDefinition } from './tools/types'

export { referenceTools } from './reference'
export type {
  FrontendAgentTools,
  CheckoutResult,
  FilterParam,
  FilterSchema,
  ListItemsSearch,
  ListItemsTool,
} from './reference'

export {
  N_CTX,
  MAX_OUTPUT_TOKENS,
  SYSTEM_CTX_WARN_FRACTION,
  HISTORY_TOKEN_BUDGET,
  estimateTokens,
} from './limits'
