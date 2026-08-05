export class MLServiceClientBase {
  constructor(protected baseUrl = defaultBaseUrl()) {}

  protected async post<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`ML service error ${response.status}: ${await response.text()}`);
    }
    return response.json() as Promise<T>;
  }
}

function defaultBaseUrl(): string {
  const candidate = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env
    ?.KEPRIX_ML_SERVICE_URL;
  return candidate ?? "http://localhost:8200";
}
