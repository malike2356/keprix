import { ClassifierClient } from "./classifier-client";
import { EmbeddingClient } from "./embedding-client";
import { HealthClient } from "./health-client";
import { LanguageClient } from "./language-client";

export class MLServiceClient extends HealthClient {}

export { ClassifierClient } from "./classifier-client";
export { EmbeddingClient } from "./embedding-client";
export { HealthClient } from "./health-client";
export { LanguageClient } from "./language-client";
export * from "./types";

export function createMLClients(baseUrl?: string) {
  return {
    embedding: new EmbeddingClient(baseUrl),
    language: new LanguageClient(baseUrl),
    classifier: new ClassifierClient(baseUrl),
    health: new HealthClient(baseUrl),
  };
}
