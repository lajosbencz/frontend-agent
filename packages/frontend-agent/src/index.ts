// Core: drive the LFM2.5-230M frontend-agent model. Framework-agnostic.

export { createAgent } from './loop/agent'
export type { Session, AgentConfig, AgentEvent, ToolCall, SubmitOptions } from './loop/agent'

export { WllamaEngine, resolveModelUrl } from './engine/wllamaEngine'
export type { WllamaEngineConfig, HFModelRef, EngineStatus } from './engine/wllamaEngine'
export { StubEngine } from './engine/stubEngine'
export type { AgentEngine, ChatMessage, EngineGenerateResult } from './engine/types'

export { buildToolGrammar, collectIds } from './engine/gbnf'

export { buildSystemPrompt } from './prompt/systemPrompt'
export type { SystemPromptConfig } from './prompt/systemPrompt'
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
