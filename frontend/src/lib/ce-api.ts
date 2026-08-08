const TOKEN_KEY = "keprix_auth_token";
const USER_KEY = "keprix_auth_user";

export type CEUser = {
  id: string;
  username: string;
  role: string;
  email?: string | null;
  workspace_id?: string | null;
  active_workspace_id?: string | null;
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

/**
 * Guard against a baked-in localhost API URL leaking into a deployed build.
 * If the build was produced with a localhost base but is now running on a
 * non-local hostname, drop the base so callers fall back to relative paths
 * (proxied by the deployed origin) instead of pointing at the browser's own
 * loopback address.
 */
export function normalizePublicApiBase(
  bakedBase: string,
  location: { hostname: string; origin: string },
): string {
  const trimmed = bakedBase.replace(/\/$/, "");
  if (!trimmed) return trimmed;
  const isBakedLocalhost = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(trimmed);
  const isRunningLocally = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (isBakedLocalhost && !isRunningLocally) {
    return "";
  }
  return trimmed;
}

const RAW_CE_API_BASE =
  process.env.NEXT_PUBLIC_CE_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "";

const CE_API_BASE =
  typeof window === "undefined"
    ? RAW_CE_API_BASE.replace(/\/$/, "")
    : normalizePublicApiBase(RAW_CE_API_BASE, window.location);

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
  const isFormData = typeof FormData !== "undefined" && options?.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...buildApiHeaders(),
    ...(options?.headers as Record<string, string> | undefined),
  };
  if (isFormData) {
    delete headers["Content-Type"];
  }
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

export class LoginChallengeError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "LoginChallengeError";
    this.code = code;
  }
}

function loginChallengeCode(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const detail = (payload as Record<string, unknown>).detail;
  if (!detail || typeof detail !== "object" || Array.isArray(detail)) {
    return null;
  }
  const code = (detail as Record<string, unknown>).code;
  return typeof code === "string" && code.trim() ? code : null;
}

export async function loginWithCredentials(
  username: string,
  password: string,
  options?: { totpCode?: string; recoveryCode?: string },
): Promise<CEUser> {
  const response = await ceApi("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({
      username,
      password,
      totp_code: options?.totpCode,
      recovery_code: options?.recoveryCode,
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const challenge = loginChallengeCode(payload);
    if (challenge === "totp_required") {
      throw new LoginChallengeError(
        challenge,
        parseApiErrorMessage(payload, "Two-factor authentication required"),
      );
    }
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
