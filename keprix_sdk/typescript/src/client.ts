import type { Domain } from "./domain.js";
import { domainToJson } from "./schema.js";
import type { ActionPlan } from "./types.js";

export class KeprixSdkClient {
  constructor(
    private readonly baseUrl: string,
    private readonly apiToken: string,
  ) {}

  async registerApp(params: {
    name: string;
    version: string;
    domain: Domain;
    webhookUrl?: string;
  }): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/api/sdk/apps/register`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: params.name,
        version: params.version,
        domain: domainToJson(params.domain),
        webhook_url: params.webhookUrl,
      }),
    });
    if (!response.ok) {
      throw new Error(`register failed: ${response.status}`);
    }
    return response.json() as Promise<Record<string, unknown>>;
  }

  async execute(appId: string, message: string, sessionId?: string): Promise<ActionPlan> {
    const response = await fetch(`${this.baseUrl}/api/sdk/execute`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ app_id: appId, message, session_id: sessionId }),
    });
    if (!response.ok) {
      throw new Error(`execute failed: ${response.status}`);
    }
    return response.json() as Promise<ActionPlan>;
  }

  async confirm(planId: string, confirmed = true): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/api/sdk/execute/confirm`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ plan_id: planId, confirmed }),
    });
    if (!response.ok) {
      throw new Error(`confirm failed: ${response.status}`);
    }
    return response.json() as Promise<Record<string, unknown>>;
  }
}
