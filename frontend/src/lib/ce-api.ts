const TOKEN_KEY = "keprix_auth_token";
const USER_KEY = "keprix_auth_user";

export type CEUser = {
  id: string;
  username: string;
  role: string;
  email?: string | null;
};

export function getCEToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getCEUser(): CEUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CEUser;
  } catch {
    return null;
  }
}

export function setCESession(token: string, user: CEUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearCESession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

const DEFAULT_BACKEND = "http://localhost:3333";

const CE_API_BASE =
  process.env.NEXT_PUBLIC_CE_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "";

const MCP_API_BASE =
  process.env.NEXT_PUBLIC_MCP_API_URL ||
  process.env.NEXT_PUBLIC_DASHBOARD_API_URL ||
  "";

export function getApiBaseUrl(): string {
  return CE_API_BASE.replace(/\/$/, "");
}

/** MCP admin API origin (servers, catalog, auto-spawn). Falls back to main API URL. */
export function getMcpApiBaseUrl(): string {
  const explicit = MCP_API_BASE.replace(/\/$/, "");
  if (explicit) return explicit;
  const main = getApiBaseUrl();
  if (main) return main;
  return DEFAULT_BACKEND;
}

/** Absolute backend origin (Swagger UI, direct openapi.json links). */
export function getBackendBaseUrl(): string {
  return getApiBaseUrl() || DEFAULT_BACKEND;
}

/** Extract a human-readable message from a FastAPI error payload. */
export function parseApiErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }
  const record = payload as Record<string, unknown>;
  const detail = record.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const detailRecord = detail as Record<string, unknown>;
    if (typeof detailRecord.error === "string" && detailRecord.error.trim()) {
      return detailRecord.error;
    }
    if (typeof detailRecord.message === "string" && detailRecord.message.trim()) {
      return detailRecord.message;
    }
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (first && typeof first === "object") {
      const msg = (first as { msg?: string }).msg;
      if (typeof msg === "string" && msg.trim()) {
        return msg;
      }
    }
  }
  if (typeof record.error === "string" && record.error.trim()) {
    return record.error;
  }
  if (typeof record.message === "string" && record.message.trim()) {
    return record.message;
  }
  return fallback;
}

export function buildApiHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const token = getCEToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const user = getCEUser();
  if (user?.id) {
    headers["X-User-ID"] = user.id;
  }
  return headers;
}

export async function ceApi(path: string, options?: RequestInit): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...buildApiHeaders(),
    ...(options?.headers as Record<string, string> | undefined),
  };
  const url = path.startsWith("http") ? path : `${CE_API_BASE}${path}`;
  return fetch(url, { ...options, headers, credentials: "include" });
}

export async function mcpApi(path: string, options?: RequestInit): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...buildApiHeaders(),
    ...(options?.headers as Record<string, string> | undefined),
  };
  const base = getMcpApiBaseUrl();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  return fetch(url, { ...options, headers, credentials: "include" });
}

export async function loginWithCredentials(username: string, password: string): Promise<CEUser> {
  const response = await ceApi("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Login failed"));
  }
  const data = (await response.json()) as { token: string; user: CEUser };
  setCESession(data.token, data.user);
  return data.user;
}

export async function fetchHealth(): Promise<{ status: string; product: string; version: string }> {
  const response = await ceApi("/api/v1/health");
  if (!response.ok) {
    throw new Error("Backend unreachable");
  }
  return response.json();
}
