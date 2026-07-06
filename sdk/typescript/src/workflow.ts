import type { KeprixClient } from "./client.js";

export type WorkflowStep = {
  id: string;
  type: "task" | "branch" | "parallel" | "approval" | "artifact";
  config?: Record<string, unknown>;
  retry?: { max_attempts?: number; delay_seconds?: number };
};

export type WorkflowEdge = {
  from: string;
  to: string;
  when?: string;
};

export type WorkflowDefinition = {
  graphId: string;
  workspaceId?: string;
  initialState?: Record<string, unknown>;
  steps: WorkflowStep[];
  edges?: WorkflowEdge[];
  entry?: string;
};

export type PlaybookRun = {
  run_id: string;
  graph_id: string;
  workspace_id: string;
  status: string;
  state: Record<string, unknown>;
  artifacts: Array<Record<string, unknown>>;
};

export class WorkflowBuilder {
  private readonly steps: WorkflowStep[] = [];
  private readonly edges: WorkflowEdge[] = [];
  private graphId: string;
  private workspaceId = "default";
  private initialState: Record<string, unknown> = {};
  private entry?: string;

  constructor(graphId: string) {
    this.graphId = graphId;
  }

  step(step: WorkflowStep): this {
    this.steps.push(step);
    return this;
  }

  task(id: string, config: Record<string, unknown> = {}, retry?: WorkflowStep["retry"]): this {
    return this.step({ id, type: "task", config, retry });
  }

  branch(id: string, key: string, equals: unknown): this {
    return this.step({ id, type: "branch", config: { key, equals } });
  }

  parallel(id: string, tasks: Array<Record<string, unknown>>): this {
    return this.step({ id, type: "parallel", config: { tasks } });
  }

  approval(id: string, message: string, risk = "medium"): this {
    return this.step({ id, type: "approval", config: { message, risk } });
  }

  artifact(id: string, name: string, fromKey?: string, content?: string): this {
    return this.step({ id, type: "artifact", config: { name, from_key: fromKey, content } });
  }

  edge(from: string, to: string, when?: string): this {
    this.edges.push({ from, to, when });
    return this;
  }

  branchTo(from: string, to: string, when: "true" | "false"): this {
    return this.edge(from, to, when);
  }

  withWorkspace(workspaceId: string): this {
    this.workspaceId = workspaceId;
    return this;
  }

  withInitialState(state: Record<string, unknown>): this {
    this.initialState = state;
    return this;
  }

  setEntry(stepId: string): this {
    this.entry = stepId;
    return this;
  }

  build(): WorkflowDefinition {
    return {
      graphId: this.graphId,
      workspaceId: this.workspaceId,
      initialState: this.initialState,
      steps: this.steps,
      edges: this.edges.length ? this.edges : undefined,
      entry: this.entry,
    };
  }
}

export function createWorkflow(graphId: string): WorkflowBuilder {
  return new WorkflowBuilder(graphId);
}

export class WorkflowRunner {
  constructor(private readonly client: KeprixClient) {}

  async start(definition: WorkflowDefinition): Promise<PlaybookRun> {
    return this.client.request<PlaybookRun>("/api/playbook-runs/start", {
      method: "POST",
      body: JSON.stringify({
        workspace_id: definition.workspaceId || "default",
        graph_id: definition.graphId,
        initial_state: definition.initialState || {},
        steps: definition.steps,
        edges: definition.edges || [],
        entry: definition.entry,
      }),
    });
  }

  async get(runId: string): Promise<PlaybookRun> {
    return this.client.request<PlaybookRun>(`/api/playbook-runs/${runId}`);
  }

  async events(runId: string) {
    return this.client.request<{ events: Array<Record<string, unknown>> }>(`/api/playbook-runs/${runId}/events`);
  }

  async resume(runId: string, statePatch: Record<string, unknown> = {}, approvedBy?: string) {
    return this.client.request<PlaybookRun>(`/api/playbook-runs/${runId}/resume`, {
      method: "POST",
      body: JSON.stringify({ state_patch: statePatch, approved_by: approvedBy }),
    });
  }

  async cancel(runId: string) {
    return this.client.request<PlaybookRun>(`/api/playbook-runs/${runId}/cancel`, { method: "POST" });
  }

  async run(definition: WorkflowDefinition): Promise<PlaybookRun> {
    const started = await this.start(definition);
    if (started.status === "waiting_for_approval") {
      const approvalStep = definition.steps.find((step) => step.type === "approval");
      const patch: Record<string, unknown> = {};
      if (approvalStep) {
        patch[`${approvalStep.id}_approved`] = true;
      }
      return this.resume(started.run_id, patch, "sdk-auto");
    }
    return started;
  }
}
