import { KeprixClient } from "./client.js";
import type { MemoryApi } from "./memory.js";
import { MemoryApi as MemoryApiImpl } from "./memory.js";
import type { ToolDefinition } from "./tools.js";
import { toOpenAiTools } from "./tools.js";

export type AgentTrace = {
  traceId: string;
  model: string;
  startedAt: string;
  events: Array<Record<string, unknown>>;
};

export type AgentConfig = {
  name: string;
  instructions: string;
  model?: string;
  tools?: ToolDefinition[];
  memory?: MemoryApi;
};

export type AgentRunInput = {
  message: string;
  sessionId?: string;
  stream?: boolean;
};

export type AgentRunResult = {
  output: string;
  raw: Record<string, unknown>;
  trace: AgentTrace;
};

export class Agent {
  readonly name: string;
  readonly instructions: string;
  readonly model: string;
  readonly tools: ToolDefinition[];
  readonly memory?: MemoryApi;
  private readonly client: KeprixClient;
  private traces: AgentTrace[] = [];

  constructor(client: KeprixClient, config: AgentConfig) {
    this.client = client;
    this.name = config.name;
    this.instructions = config.instructions;
    this.model = config.model || "keprix";
    this.tools = config.tools || [];
    this.memory = config.memory;
  }

  static define(client: KeprixClient, config: AgentConfig): Agent {
    return new Agent(client, config);
  }

  attachTools(...tools: ToolDefinition[]): this {
    this.tools.push(...tools);
    return this;
  }

  attachMemory(memory: MemoryApi): this {
    (this as { memory?: MemoryApi }).memory = memory;
    return this;
  }

  private async buildMessages(message: string, sessionId?: string) {
    const messages: Array<{ role: string; content: string }> = [
      { role: "system", content: this.instructions },
    ];
    if (this.memory && sessionId) {
      try {
        const session = await this.memory.listConversationHistory(sessionId);
        for (const row of session.messages || []) {
          if (typeof row === "object" && row && "role" in row && "content" in row) {
            messages.push({ role: String((row as { role: string }).role), content: String((row as { content: string }).content) });
          }
        }
      } catch {
        // Session may not exist yet; continue with system + user only.
      }
    }
    messages.push({ role: "user", content: message });
    return messages;
  }

  async run(input: AgentRunInput): Promise<AgentRunResult> {
    const trace: AgentTrace = {
      traceId: crypto.randomUUID(),
      model: this.model,
      startedAt: new Date().toISOString(),
      events: [{ type: "agent.run.started", agent: this.name }],
    };
    const messages = await this.buildMessages(input.message, input.sessionId);
    const body: Record<string, unknown> = {
      model: this.model,
      messages,
      metadata: { agent: this.name, trace_id: trace.traceId },
    };
    if (this.tools.length) {
      body.tools = toOpenAiTools(this.tools);
    }
    const raw = await this.client.request<Record<string, unknown>>("/v1/chat/completions", {
      method: "POST",
      body: JSON.stringify(body),
    });
    const output = extractAssistantText(raw);
    trace.events.push({ type: "agent.run.completed", output_length: output.length });
    this.traces.push(trace);
    return { output, raw, trace };
  }

  async *stream(input: AgentRunInput): AsyncGenerator<string, AgentRunResult, void> {
    const trace: AgentTrace = {
      traceId: crypto.randomUUID(),
      model: this.model,
      startedAt: new Date().toISOString(),
      events: [{ type: "agent.run.stream_started", agent: this.name }],
    };
    const messages = await this.buildMessages(input.message, input.sessionId);
    const response = await this.client.stream("/v1/chat/completions", {
      method: "POST",
      body: JSON.stringify({
        model: this.model,
        messages,
        stream: true,
        metadata: { agent: this.name, trace_id: trace.traceId },
      }),
    });
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("Streaming response has no body");
    }
    const decoder = new TextDecoder();
    let buffer = "";
    let output = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (!payload || payload === "[DONE]") continue;
        const chunk = JSON.parse(payload) as Record<string, unknown>;
        const delta = extractStreamDelta(chunk);
        if (delta) {
          output += delta;
          yield delta;
        }
      }
    }
    trace.events.push({ type: "agent.run.stream_completed", output_length: output.length });
    this.traces.push(trace);
    return { output, raw: {}, trace };
  }

  listTraces(): AgentTrace[] {
    return [...this.traces];
  }

  async evaluate(cases: Array<{ input: string; expect_contains?: string }>) {
    const results = [];
    for (const testCase of cases) {
      const run = await this.run({ message: testCase.input });
      const passed = testCase.expect_contains ? run.output.includes(testCase.expect_contains) : run.output.length > 0;
      results.push({ input: testCase.input, passed, output: run.output, trace: run.trace });
    }
    return {
      agent: this.name,
      passed: results.filter((row) => row.passed).length,
      total: results.length,
      cases: results,
    };
  }
}

function extractAssistantText(payload: Record<string, unknown>): string {
  const choices = payload.choices as Array<Record<string, unknown>> | undefined;
  const message = choices?.[0]?.message as Record<string, unknown> | undefined;
  return String(message?.content || "");
}

function extractStreamDelta(payload: Record<string, unknown>): string {
  const choices = payload.choices as Array<Record<string, unknown>> | undefined;
  const delta = choices?.[0]?.delta as Record<string, unknown> | undefined;
  return String(delta?.content || "");
}

export function createMemoryApi(client: KeprixClient): MemoryApi {
  return new MemoryApiImpl(client);
}
