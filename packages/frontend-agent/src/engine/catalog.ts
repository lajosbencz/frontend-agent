import { type HFModelRef, resolveModelRef, resolveModelUrl } from './wllamaEngine'

/** A selectable published model: pass the chosen option's `ref` into a fresh {@link WllamaEngine}
 *  to switch (GGUF is OPFS-cached per URL, so re-selecting is instant). */
export interface ModelOption {
  id: string
  label: string
  size: '230M' | '350M'
  ref: Required<HFModelRef>
  /** Approx download size in MB, shown before the file is fetched. */
  approxMB: number
  /** True for the smallest-footprint quant of each size (browser default). */
  smallest?: boolean
}

const REPO_230 = 'lazos/lfm2.5-230m-frontend-agent'
const REPO_350 = 'lazos/lfm2.5-350m-frontend-agent'
const VERSION = 'main'

/** The published models, smallest first. Version floats to `main` (latest release); pin a specific
 *  `ref.version` (e.g. `v1.2.0`) for a fixed build. */
export const FRONTEND_AGENT_MODELS: ModelOption[] = [
  { id: '230m-q4', label: 'LFM2.5 230M (Q4_K_M)', size: '230M',
    ref: { repo: REPO_230, version: VERSION, quant: 'Q4_K_M' }, approxMB: 153, smallest: true },
  { id: '230m-q6', label: 'LFM2.5 230M (Q6_K)', size: '230M',
    ref: { repo: REPO_230, version: VERSION, quant: 'Q6_K' }, approxMB: 191 },
  { id: '230m-q8', label: 'LFM2.5 230M (Q8_0)', size: '230M',
    ref: { repo: REPO_230, version: VERSION, quant: 'Q8_0' }, approxMB: 247 },
  { id: '350m-q4', label: 'LFM2.5 350M (Q4_K_M)', size: '350M',
    ref: { repo: REPO_350, version: VERSION, quant: 'Q4_K_M' }, approxMB: 230, smallest: true },
  { id: '350m-q6', label: 'LFM2.5 350M (Q6_K)', size: '350M',
    ref: { repo: REPO_350, version: VERSION, quant: 'Q6_K' }, approxMB: 293 },
  { id: '350m-q8', label: 'LFM2.5 350M (Q8_0)', size: '350M',
    ref: { repo: REPO_350, version: VERSION, quant: 'Q8_0' }, approxMB: 379 },
]

/** Default selection: the smallest 230M build (fastest cold start). */
export const DEFAULT_MODEL_ID = '230m-q4'

/** The size (rows) and quant (columns) axes of the model matrix, in display order. */
export const MODEL_SIZES = ['230M', '350M'] as const
export const MODEL_QUANTS = [
  { quant: 'Q4_K_M', short: 'Q4', note: 'smallest' },
  { quant: 'Q6_K', short: 'Q6', note: 'balanced' },
  { quant: 'Q8_0', short: 'Q8', note: 'near-lossless' },
] as const

/** Short quant label, e.g. `Q6_K` -> `Q6`. */
export function shortQuant(quant: string): string {
  return MODEL_QUANTS.find((q) => q.quant === quant)?.short ?? quant
}

/** The catalog option at a (size, quant) matrix cell, if any. */
export function modelOptionAt(size: string, quant: string): ModelOption | undefined {
  return FRONTEND_AGENT_MODELS.find((m) => m.size === size && m.ref.quant === quant)
}

/** Look up an option by id (falls back to the default). */
export function modelOptionById(id: string | undefined): ModelOption {
  return FRONTEND_AGENT_MODELS.find((m) => m.id === id)
    ?? FRONTEND_AGENT_MODELS.find((m) => m.id === DEFAULT_MODEL_ID)!
}

/** Best-effort: find the catalog option matching a resolved ref (repo+quant), for reflecting an
 *  externally-configured model back onto a picker. Version is ignored (a floating ref still maps). */
export function modelOptionForRef(ref: HFModelRef): ModelOption | undefined {
  const r = resolveModelRef(ref)
  return FRONTEND_AGENT_MODELS.find((m) => m.ref.repo === r.repo && m.ref.quant === r.quant)
}

/** The GGUF URL for a catalog option; same resolver the engine uses. */
export function modelOptionUrl(opt: ModelOption): string {
  return resolveModelUrl(opt.ref)
}
