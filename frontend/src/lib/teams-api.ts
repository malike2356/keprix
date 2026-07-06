import { ceApi } from "@/lib/ce-api";

export type TeamSummary = {
  name: string;
  roles: string[];
  tasks: Array<{ id: string; description?: string; role?: string; expected_output?: string }>;
  flow: { start: string; events?: unknown[] };
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || fallback);
  }
  return (await response.json()) as T;
}

export async function fetchTeams(): Promise<string[]> {
  const payload = await parseJson<{ teams: string[] }>(
    await ceApi("/api/teams"),
    "Failed to load teams",
  );
  return payload.teams || [];
}

export async function fetchTeam(name: string): Promise<TeamSummary> {
  return parseJson<TeamSummary>(
    await ceApi(`/api/teams/${encodeURIComponent(name)}`),
    "Failed to load team",
  );
}

export async function fetchTeamYaml(name: string): Promise<string> {
  const payload = await parseJson<{ yaml: string }>(
    await ceApi(`/api/teams/${encodeURIComponent(name)}/yaml`),
    "Failed to load team YAML",
  );
  return payload.yaml;
}

export async function importTeam(yaml: string): Promise<{ name: string; tasks: string[]; flow_start: string }> {
  return parseJson(
    await ceApi("/api/teams/import", {
      method: "POST",
      body: JSON.stringify({ yaml }),
    }),
    "Import failed",
  );
}

export async function runTeam(
  name: string,
  objective: string,
): Promise<{
  name: string;
  run_id: string;
  status: string;
  state: Record<string, unknown>;
  events_url?: string;
  workspace_url?: string;
}> {
  return parseJson(
    await ceApi(`/api/teams/${encodeURIComponent(name)}/run`, {
      method: "POST",
      body: JSON.stringify({ objective }),
    }),
    "Run failed",
  );
}

export type TeamRunEvent = {
  event_type: string;
  role?: string | null;
  task_id?: string | null;
  content: string;
  payload?: Record<string, unknown>;
  timestamp: string;
};

export async function fetchTeamRunEvents(
  teamName: string,
  runId: string,
): Promise<{ team_name: string; run_id: string; status: string; events: TeamRunEvent[] }> {
  return parseJson(
    await ceApi(`/api/teams/${encodeURIComponent(teamName)}/runs/${encodeURIComponent(runId)}/events`),
    "Failed to load crew run events",
  );
}

export const SAMPLE_TEAM_YAML = `name: sample-crew
roles:
  builder:
    goal: Build features
    backstory: Senior engineer
tasks:
  build:
    description: Implement the requested change
    role: builder
    expected_output: result.json
flow:
  start: build
`;
