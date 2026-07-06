import { KeprixSdkClient } from "./client.js";
import type { Domain } from "./domain.js";
import type { ActionPlan, ExecutionResult } from "./types.js";

export type ActionHandler = (plan: ActionPlan) => Promise<ExecutionResult> | ExecutionResult;

export interface CarinaAppOptions {
  name: string;
  keprixUrl?: string;
  carinaUrl?: string;
  apiToken: string;
}

export class KeprixApp {
  readonly name: string;
  readonly keprixUrl: string;
  readonly apiToken: string;
  readonly version = "1.0.0";
  private readonly domains: Domain[] = [];
  private readonly client: KeprixSdkClient;
  private appId: string | null = null;
  private webhookUrl: string | undefined;
  private actionCallback: ActionHandler | null = null;

  constructor(options: CarinaAppOptions) {
    this.name = options.name;
    this.keprixUrl = (options.carinaUrl || options.keprixUrl || "http://localhost:3333").replace(/\/$/, "");
    this.apiToken = options.apiToken;
    this.client = new KeprixSdkClient(this.keprixUrl, this.apiToken);
  }

  registerDomain(domain: Domain): void {
    this.domains.push(domain);
  }

  onAction(callback: ActionHandler): ActionHandler {
    this.actionCallback = callback;
    return callback;
  }

  async connect(webhookUrl?: string): Promise<string> {
    this.webhookUrl = webhookUrl;
    const domain = this.domains[0] || { name: "default", entities: [] };
    const result = await this.client.registerApp({
      name: this.name,
      version: this.version,
      domain,
      webhookUrl,
    });
    this.appId = String(result.app_id);
    return this.appId;
  }

  async handle(text: string, sessionId?: string): Promise<ActionPlan> {
    if (!this.appId) {
      await this.connect(this.webhookUrl);
    }
    return this.client.execute(this.appId as string, text, sessionId);
  }

  async confirm(planId: string, confirmed = true): Promise<Record<string, unknown>> {
    return this.client.confirm(planId, confirmed);
  }

  async start(): Promise<void> {
    await this.connect(this.webhookUrl);
    if (!this.actionCallback) {
      return;
    }
    while (true) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
}

export const CarinaApp = KeprixApp;
