export { createFrontendAgent } from './createFrontendAgent'
export type { FrontendAgentConfig, ViewSource, CartLineSource } from './createFrontendAgent'

export { createAgent } from './loop/agent'
export type { Session, AgentConfig, AgentEvent, ToolCall, SubmitOptions } from './loop/agent'

export { WllamaEngine, resolveModelUrl, resolveModelRef, fetchModelMeta } from './engine/wllamaEngine'
export type { WllamaEngineConfig, HFModelRef, EngineStatus, ModelFileMeta } from './engine/wllamaEngine'
export {
  FRONTEND_AGENT_MODELS,
  DEFAULT_MODEL_ID,
  MODEL_SIZES,
  MODEL_QUANTS,
  shortQuant,
  modelOptionAt,
  modelOptionById,
  modelOptionForRef,
  modelOptionUrl,
} from './engine/catalog'
export type { ModelOption } from './engine/catalog'
export { StubEngine } from './engine/stubEngine'
export type { AgentEngine, ChatMessage, EngineGenerateResult } from './engine/types'

export { buildToolGrammar, collectIds } from './engine/gbnf'

export { buildSystemPrompt } from './prompt/systemPrompt'
export type { SystemPromptConfig } from './prompt/systemPrompt'

export {
  renderContext,
  CONTEXT_SCHEMA_VERSION,
  ContextManager,
} from './context'
export type {
  ContextInput,
  ViewItem,
  CartItem,
  KnowledgeSnippet,
  ContextManagerConfig,
} from './context'
export { pyJson } from './prompt/pyJson'

export { parseToolCalls } from './parsing/toolCallParser'
export type { ParsedToolCall, ParseResult } from './parsing/toolCallParser'
export { renderToolCalls } from './parsing/renderToolCalls'

export { buildRegistry } from './tools/registry'
export type { ToolRegistry } from './tools/registry'
export type { ToolSchema, ToolHandler, ToolDefinition } from './tools/types'

export {
  N_CTX,
  MAX_OUTPUT_TOKENS,
  SYSTEM_CTX_WARN_FRACTION,
  HISTORY_TOKEN_BUDGET,
  estimateTokens,
} from './limits'
