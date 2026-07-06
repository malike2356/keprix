export type KeprixClientOptions = {
  baseUrl?: string;
  apiKey?: string;
  userId?: string;
  fetchImpl?: typeof fetch;
};

export class KeprixHttpError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`Keprix API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

export class KeprixClient {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly userId: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: KeprixClientOptions = {}) {
    this.baseUrl = (options.baseUrl || process.env.KEPRIX_BASE_URL || "http://localhost:3333").replace(/\/$/, "");
    this.apiKey = options.apiKey || process.env.KEPRIX_API_KEY || "";
    this.userId = options.userId || process.env.KEPRIX_USER_ID || "default";
    this.fetchImpl = options.fetchImpl || fetch;
  }

  headers(extra: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-User-Id": this.userId,
      ...extra,
    };
    if (this.apiKey) {
      headers.Authorization = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      ...init,
      headers: this.headers((init.headers as Record<string, string>) || {}),
    });
    const text = await response.text();
    const body = text ? JSON.parse(text) : null;
    if (!response.ok) {
      throw new KeprixHttpError(response.status, body);
    }
    return body as T;
  }

  async stream(path: string, init: RequestInit = {}): Promise<Response> {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      ...init,
      headers: this.headers((init.headers as Record<string, string>) || {}),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new KeprixHttpError(response.status, text ? JSON.parse(text) : null);
    }
    return response;
  }
}
