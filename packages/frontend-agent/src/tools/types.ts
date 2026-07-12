export interface ToolSchema {
  name: string
  description: string
  parameters: {
    type: 'object'
    properties: Record<string, unknown>
    required?: string[]
  }
}

export type ToolHandler = (args: Record<string, unknown>) => Promise<unknown> | unknown

export interface ToolDefinition {
  schema: ToolSchema
  handler: ToolHandler
}
