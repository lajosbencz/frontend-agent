// `frontend-agent/wllama` - the in-browser WASM engine and the published-model catalog. This is the
// ONLY entry that pulls @wllama/wllama; keep it out of `frontend-agent/core` so pure consumers don't
// pay for the WASM/TS. Next/webpack users who DO import it may need `transpilePackages: ['@wllama/wllama']`.

export { WllamaEngine, resolveModelUrl, resolveModelRef, fetchModelMeta } from './engine/wllamaEngine'
export type {
  WllamaEngineConfig,
  HFModelRef,
  EngineStatus,
  ModelFileMeta,
} from './engine/wllamaEngine'

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
