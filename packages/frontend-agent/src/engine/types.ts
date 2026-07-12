export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  name?: string
}

export interface EngineGenerateResult {
  /** Plain-text portion of the reply (tool-call markers stripped). */
  text: string
  /** Parsed tool calls, if the model emitted any. */
  toolCalls: { name: string; args: Record<string, unknown> }[]
  /**
   * The assistant turn exactly as it should be replayed into the next generation's
   * context - includes the raw <|tool_call_start|>...<|tool_call_end|> markers when the
   * model called tools, so multi-turn context matches how the model was trained.
   */
  raw: string
}

/**
 * Implemented by both the stub engine and the real wllama engine so useAgentLoop
 * doesn't need to know which it's driving. `messages` is the full model-format
 * conversation (including the system message).
 */
export interface AgentEngine {
  /** Eagerly download/initialize the model (and detect the backend) at activation time. */
  load?(): Promise<void>
  /**
   * `grammar` (GBNF) constrains decoding to valid tool-call structure + id-grounding when provided;
   * the loop rebuilds it each turn from the tool schema and the ids seen in results so far.
   */
  generate(messages: ChatMessage[], grammar?: string): Promise<EngineGenerateResult>
}
