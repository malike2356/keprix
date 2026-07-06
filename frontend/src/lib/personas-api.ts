import { ceApi } from "@/lib/ce-api";

export type Persona = {
  name: string;
  role: string;
  tone: string;
  colour: string;
  agent_type: string;
  skill_packs: string[];
  system_prompt?: string;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export async function fetchPersonas() {
  return parseJson<{ personas: Persona[] }>(await ceApi("/api/personas"), "personas");
}

export async function fetchPersona(name: string) {
  return parseJson<Persona>(await ceApi(`/api/personas/${encodeURIComponent(name)}`), "persona");
}
