import { pyJson } from './pyJson'
import type { ToolSchema } from '../tools/types'

export interface SystemPromptConfig {
  /** 1-2 line persona/rules for this deployment (who the assistant is, grounding + refusal rules). */
  persona: string
  /** The tool schemas to advertise (same array the loop dispatches). */
  toolSchemas: ToolSchema[]
  /** A short "headline entities" hint (`Title [id]; ...`) or a provider for it. Optional. */
  catalogHint?: string | (() => string | Promise<string>)
  /** Label before the hint. Defaults to the trained `"Example catalog items"`. */
  hintLabel?: string
}

/**
 * Reproduce the exact v1.0.0 system message the model was trained on:
 *   `{persona}\n\n{hintLabel}: {hint}\nList of tools: [{fn-json}, ...]`
 * The tool list uses Python `json.dumps` separators (`pyJson`) for byte-for-byte train/inference
 * parity. The full system text is baked here (pass NO `tools` array to the engine's chat template).
 */
export async function buildSystemPrompt(cfg: SystemPromptConfig): Promise<string> {
  const label = cfg.hintLabel ?? 'Example catalog items'
  const hint =
    typeof cfg.catalogHint === 'function' ? await cfg.catalogHint() : cfg.catalogHint
  const head = hint ? `${cfg.persona}\n\n${label}: ${hint}` : cfg.persona
  const tools = cfg.toolSchemas.map((s) => pyJson({ type: 'function', function: s }))
  return `${head}\nList of tools: [${tools.join(', ')}]`
}
