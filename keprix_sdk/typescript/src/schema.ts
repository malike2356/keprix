import type { Domain } from "./domain.js";

export function domainToJson(domain: Domain): Record<string, unknown> {
  return {
    name: domain.name,
    entities: (domain.entities || []).map((entity) => ({
      name: entity.name,
      fields: (entity.fields || []).map((field) => ({
        name: field.name,
        type: field.type ?? "string",
        required: field.required ?? false,
        default: field.default,
        entity: field.entity,
        values: field.values,
      })),
      operations: (entity.operations || []).map((operation) => ({
        name: operation.name,
        confirmation_required: operation.confirmation_required ?? false,
      })),
    })),
  };
}
