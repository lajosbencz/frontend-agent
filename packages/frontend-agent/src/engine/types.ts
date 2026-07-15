export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
}

export interface EngineGenerateResult {
  /** Plain-text portion of the reply (tool-call markers stripped). */
  text: string
  toolCalls: { name: string; args: Record<string, unknown> }[]
  /** The assistant turn to replay into the next generation - keeps the raw tool-call markers so
   *  multi-turn context matches training. */
  raw: string
}

/** Implemented by both StubEngine and WllamaEngine. `messages` is the full model-format
 *  conversation (including the system message). */
export interface AgentEngine {
  /** Eagerly download/initialize the model (and detect the backend) at activation time. */
  load?(): Promise<void>
  /** `grammar` (GBNF) constrains decoding to valid tool-call structure + id-grounding when provided. */
  generate(messages: ChatMessage[], grammar?: string): Promise<EngineGenerateResult>
}
