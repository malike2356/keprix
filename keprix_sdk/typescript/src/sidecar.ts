/** Keprix Universal Sidecar HTTP client (`/sidecar/v1`). */

export type SidecarClientOptions = {
  baseUrl: string;
  token?: string;
  projectKey?: string;
  timeoutMs?: number;
  webhookSecret?: string;
};

export class SidecarClient {
  baseUrl: string;
  token: string;
  projectKey?: string;
  timeoutMs: number;
  webhookSecret?: string;
  private prefix: string;

  constructor(options: SidecarClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.token = options.token || "";
    this.projectKey = options.projectKey;
    this.timeoutMs = options.timeoutMs ?? 60_000;
    this.webhookSecret = options.webhookSecret;
    this.prefix = `${this.baseUrl}/sidecar/v1`;
  }

  private headers(extra?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    return { ...headers, ...(extra || {}) };
  }

  private project(projectKey?: string): string {
    const key = projectKey || this.projectKey;
    if (!key) throw new Error("projectKey is required");
    return key;
  }

  private async request(
    method: string,
    path: string,
    body?: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await fetch(`${this.prefix}${path}`, {
        method,
        headers: this.headers(),
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
      const text = await response.text();
      if (!response.ok) {
        throw new Error(`${method} ${path} failed: ${response.status} ${text}`);
      }
      if (!text) return {};
      return JSON.parse(text) as Record<string, unknown>;
    } finally {
      clearTimeout(timer);
    }
  }

  async pairBootstrap(params: {
    pairingCode: string;
    projectKey?: string;
    deployment?: string;
    environment?: string;
    requestedScopes?: string[];
  }): Promise<Record<string, unknown>> {
    const result = await this.request("POST", "/pair/bootstrap", {
      pairing_code: params.pairingCode,
      project_key: this.project(params.projectKey),
      deployment: params.deployment || "local-dev",
      environment: params.environment || "local",
      requested_scopes: params.requestedScopes,
    });
    const token = (result.access_token || result.token) as string | undefined;
    if (token) this.token = token;
    return result;
  }

  async health(projectKey?: string): Promise<Record<string, unknown>> {
    const key = projectKey || this.projectKey;
    if (key) return this.request("GET", `/projects/${key}/health`);
    return this.request("GET", "/health");
  }

  async capabilities(projectKey?: string): Promise<Record<string, unknown>> {
    const key = this.project(projectKey);
    return this.request("GET", `/projects/${key}/capabilities`);
  }

  async session(params: {
    purpose: string;
    tenantId: string;
    actorId: string;
    projectKey?: string;
    grants?: string[];
  }): Promise<Record<string, unknown>> {
    const key = this.project(params.projectKey);
    return this.request("POST", `/projects/${key}/sessions`, {
      purpose: params.purpose,
      tenant_id: params.tenantId,
      actor_id: params.actorId,
      grants: params.grants,
    });
  }

  async invoke(params: {
    node: string;
    input?: Record<string, unknown>;
    purpose?: string;
    projectKey?: string;
    sessionId?: string;
  }): Promise<Record<string, unknown>> {
    const key = this.project(params.projectKey);
    return this.request("POST", `/projects/${key}/invoke`, {
      node: params.node,
      input: params.input || {},
      purpose: params.purpose || "invoke",
      session_id: params.sessionId,
    });
  }

  async jobs(params: {
    node: string;
    input?: Record<string, unknown>;
    purpose?: string;
    projectKey?: string;
    idempotencyKey?: string;
  }): Promise<Record<string, unknown>> {
    const key = this.project(params.projectKey);
    return this.request("POST", `/projects/${key}/jobs`, {
      node: params.node,
      input: params.input || {},
      purpose: params.purpose || "job",
      idempotency_key: params.idempotencyKey,
    });
  }

  async getJob(jobId: string, projectKey?: string): Promise<Record<string, unknown>> {
    const key = this.project(projectKey);
    return this.request("GET", `/projects/${key}/jobs/${jobId}`);
  }

  async cancel(jobId: string, projectKey?: string): Promise<Record<string, unknown>> {
    const key = this.project(projectKey);
    return this.request("POST", `/projects/${key}/jobs/${jobId}/cancel`, {});
  }

  async sendEvent(
    event: Record<string, unknown>,
    projectKey?: string,
  ): Promise<Record<string, unknown>> {
    const key = this.project(projectKey);
    return this.request("POST", `/projects/${key}/events`, event);
  }

  async *streamEvents(projectKey?: string): AsyncGenerator<Record<string, unknown>> {
    const key = this.project(projectKey);
    const response = await fetch(`${this.prefix}/projects/${key}/events/stream`, {
      headers: this.headers(),
    });
    if (!response.ok || !response.body) {
      throw new Error(`stream failed: ${response.status}`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let dataLines: string[] = [];
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trimStart());
        } else if (line === "" && dataLines.length) {
          const raw = dataLines.join("\n");
          dataLines = [];
          try {
            yield JSON.parse(raw) as Record<string, unknown>;
          } catch {
            yield { raw };
          }
        }
      }
    }
  }

  async approvalDecision(params: {
    approvalId: string;
    decision: string;
    actorId: string;
    projectKey?: string;
    reason?: string;
  }): Promise<Record<string, unknown>> {
    const key = this.project(params.projectKey);
    return this.request("POST", `/projects/${key}/approvals/${params.approvalId}/decision`, {
      decision: params.decision,
      actor_id: params.actorId,
      reason: params.reason,
    });
  }

  async verifyWebhook(params: {
    body: string | ArrayBuffer | Uint8Array;
    signatureHeader: string;
    timestampHeader?: string;
    maxSkewSeconds?: number;
    secret?: string;
  }): Promise<boolean> {
    const secret = params.secret || this.webhookSecret;
    if (!secret) throw new Error("webhook secret required");
    const enc = new TextEncoder();
    let raw: Uint8Array;
    if (typeof params.body === "string") raw = enc.encode(params.body);
    else if (params.body instanceof ArrayBuffer) raw = new Uint8Array(params.body);
    else raw = params.body;

    let provided = params.signatureHeader.trim();
    let ts: string | undefined;
    if (provided.includes("v1=")) {
      const parts: Record<string, string> = {};
      for (const piece of provided.split(",")) {
        const [k, v] = piece.split("=", 2);
        if (k && v) parts[k] = v;
      }
      ts = parts.t;
      provided = parts.v1 || "";
    }
    if (params.timestampHeader && ts === undefined) ts = params.timestampHeader;
    const maxSkew = params.maxSkewSeconds ?? 300;
    let signed: Uint8Array = raw;
    if (ts !== undefined) {
      const tsNum = Number(ts);
      if (!Number.isFinite(tsNum) || Math.abs(Date.now() / 1000 - tsNum) > maxSkew) {
        return false;
      }
      const prefix = enc.encode(`${ts}.`);
      signed = new Uint8Array(prefix.length + raw.length);
      signed.set(prefix, 0);
      signed.set(raw, prefix.length);
    }
    const key = await crypto.subtle.importKey(
      "raw",
      enc.encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
    const sig = await crypto.subtle.sign("HMAC", key, signed);
    const hex = Array.from(new Uint8Array(sig))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    return hex === provided.toLowerCase();
  }

  async connectorTest(params: {
    connectorKey: string;
    pathParams?: Record<string, unknown>;
    projectKey?: string;
  }): Promise<Record<string, unknown>> {
    const key = this.project(params.projectKey);
    return this.request("POST", `/projects/${key}/connectors/${params.connectorKey}/test`, {
      path_params: params.pathParams || {},
    });
  }
}
