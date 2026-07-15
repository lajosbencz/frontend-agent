import type { ToolDefinition, ToolHandler, ToolSchema } from './types'

export interface ToolRegistry {
  /** Tool schemas, in order - injected into the system prompt (order is contract-significant). */
  schemas: ToolSchema[]
  /** name -> handler dispatch map. */
  handlers: Record<string, ToolHandler>
}

/** Build a registry from a consumer-supplied tool set. Bring your own tools, or use `referenceTools`. */
export function buildRegistry(definitions: ToolDefinition[]): ToolRegistry {
  return {
    schemas: definitions.map((d) => d.schema),
    handlers: Object.fromEntries(definitions.map((d) => [d.schema.name, d.handler])),
  }
}
