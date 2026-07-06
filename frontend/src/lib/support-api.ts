import { ceApi } from "@/lib/ce-api";

export type SupportTicket = {
  id: string;
  category: string;
  subject: string;
  description: string;
  status: string;
  created_at: string;
  diagnostics_attached?: boolean;
};

export type ChecklistItem = {
  id: string;
  label: string;
  completed: boolean;
  category: string;
};

export type Incident = {
  id: string;
  title: string;
  severity: string;
  status: string;
  summary: string;
  started_at: string;
  public_post?: string | null;
};

export async function fetchSupportChecklist(): Promise<{
  items: ChecklistItem[];
  progress: { total: number; completed: number; percent: number };
}> {
  const response = await ceApi("/api/support/onboarding/checklist");
  if (!response.ok) throw new Error("Failed to load checklist");
  return response.json();
}

export async function updateSupportChecklist(itemId: string, completed: boolean) {
  const response = await ceApi("/api/support/onboarding/checklist", {
    method: "PATCH",
    body: JSON.stringify({ item_id: itemId, completed }),
  });
  if (!response.ok) throw new Error("Failed to update checklist");
  return response.json();
}

export async function fetchDiagnosticsBundle() {
  const response = await ceApi("/api/support/diagnostics/bundle", { method: "POST" });
  if (!response.ok) throw new Error("Failed to build diagnostics bundle");
  return response.json();
}

export async function createSupportTicket(body: {
  category: string;
  subject: string;
  description: string;
  attach_diagnostics?: boolean;
}) {
  const response = await ceApi("/api/support/tickets", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to create ticket");
  return response.json();
}

export async function fetchSupportTickets(): Promise<{ tickets: SupportTicket[] }> {
  const response = await ceApi("/api/support/tickets");
  if (!response.ok) throw new Error("Failed to load tickets");
  return response.json();
}

export async function fetchCommunityLinks() {
  const response = await ceApi("/api/support/community");
  if (!response.ok) throw new Error("Failed to load community links");
  return response.json();
}

export async function fetchSetupRescue() {
  const response = await ceApi("/api/support/setup-rescue");
  if (!response.ok) throw new Error("Failed to load setup rescue steps");
  return response.json();
}

export async function createHandoff(body: {
  category: string;
  summary: string;
  privacy: "minimal" | "standard";
  contact_email?: string;
}) {
  const response = await ceApi("/api/support/handoff", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to create handoff");
  return response.json();
}

export async function generateIncidentPost(incidentId: string) {
  const response = await ceApi(`/api/support/incidents/${incidentId}/public-post`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to generate incident post");
  return response.json();
}

export async function createIncident(body: { title: string; severity: string; summary: string }) {
  const response = await ceApi("/api/support/incidents", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to create incident");
  return response.json();
}

export async function fetchIncidents(): Promise<{ incidents: Incident[] }> {
  const response = await ceApi("/api/support/incidents");
  if (!response.ok) throw new Error("Failed to load incidents");
  return response.json();
}
