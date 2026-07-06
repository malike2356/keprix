export type ToolParameterSchema = {
  type: "object" | "string" | "number" | "boolean";
  properties?: Record<string, { type: string; description?: string }>;
  required?: string[];
};

export type ToolDefinition = {
  name: string;
  description: string;
  parameters: ToolParameterSchema;
};

export function defineTool(
  name: string,
  description: string,
  parameters: ToolParameterSchema,
): ToolDefinition {
  return { name, description, parameters };
}

export function toOpenAiTools(tools: ToolDefinition[]) {
  return tools.map((tool) => ({
    type: "function" as const,
    function: {
      name: tool.name,
      description: tool.description,
      parameters: tool.parameters,
    },
  }));
}
