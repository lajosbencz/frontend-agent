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

/** Reproduce the trained system message: `{persona}\n\n{hintLabel}: {hint}\nList of tools: [...]`,
 *  tool list rendered with `pyJson` for train/inference parity. Pass NO `tools` array to the engine.
 *
 *  The `List of tools: [...]` literal and the pyJson rendering are LFM2.5 chat-template parity (they
 *  match how the base model was trained to receive tool schemas) - not an arbitrary wrapper. Change
 *  them only if you retrain with a different convention. `persona` here is the full C block (persona
 *  + injected context), and `hintLabel` is the one freely-configurable label. */
export async function buildSystemPrompt(cfg: SystemPromptConfig): Promise<string> {
  const label = cfg.hintLabel ?? 'Example catalog items'
  const hint =
    typeof cfg.catalogHint === 'function' ? await cfg.catalogHint() : cfg.catalogHint
  const head = hint ? `${cfg.persona}\n\n${label}: ${hint}` : cfg.persona
  const tools = cfg.toolSchemas.map((s) => pyJson({ type: 'function', function: s }))
  return `${head}\nList of tools: [${tools.join(', ')}]`
}
