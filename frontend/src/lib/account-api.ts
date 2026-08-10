import { CEUser, ceApi, getApiBaseUrl, getCEToken, parseApiErrorMessage, setCESession } from "@/lib/ce-api";

export type AccountProfile = CEUser & {
  display_name?: string;
  avatar_url?: string | null;
  locale?: string | null;
  timezone?: string | null;
  totp_enabled?: boolean;
  is_approved?: boolean;
  created_at?: number | null;
};

export type AccountProfileUpdate = {
  display_name?: string;
  email?: string;
  avatar_url?: string;
  locale?: string;
  timezone?: string;
};

export async function fetchAccountProfile(): Promise<AccountProfile> {
  const response = await ceApi("/api/auth/me");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to load profile"));
  }
  const data = (await response.json()) as { user?: AccountProfile };
  if (!data.user) {
    throw new Error("Profile not found");
  }
  return data.user;
}

export async function updateAccountProfile(payload: AccountProfileUpdate): Promise<AccountProfile> {
  const response = await ceApi("/api/auth/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to update profile"));
  }
  const data = (await response.json()) as { user?: AccountProfile };
  if (!data.user) {
    throw new Error("Profile update returned no user");
  }
  const token = getCEToken();
  if (token) {
    setCESession(token, data.user);
  }
  return data.user;
}

export async function changeAccountPassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const response = await ceApi("/api/auth/me/password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to change password"));
  }
}

export async function requestPasswordReset(emailOrUsername: string): Promise<string> {
  const response = await ceApi("/api/auth/password/forgot", {
    method: "POST",
    body: JSON.stringify({ email_or_username: emailOrUsername }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to request password reset"));
  }
  const data = (await response.json()) as { message?: string };
  return data.message ?? "If an account exists, a reset link was sent.";
}

export async function resetPasswordWithToken(token: string, newPassword: string): Promise<void> {
  const response = await ceApi("/api/auth/password/reset", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to reset password"));
  }
}

export type TotpSetupResponse = {
  secret: string;
  provisioning_uri: string;
};

export async function setupTotp(): Promise<TotpSetupResponse> {
  const response = await ceApi("/api/auth/totp/setup", { method: "POST" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to start two-factor setup"));
  }
  return response.json() as Promise<TotpSetupResponse>;
}

export async function fetchTotpQrBlobUrl(provisioningUri: string): Promise<string> {
  const response = await ceApi("/api/auth/totp/qr", {
    method: "POST",
    body: JSON.stringify({ provisioning_uri: provisioningUri }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to load QR code"));
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function verifyTotp(code: string): Promise<string[]> {
  const response = await ceApi("/api/auth/totp/verify", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Invalid verification code"));
  }
  const data = (await response.json()) as { recovery_codes?: string[] };
  return data.recovery_codes ?? [];
}

export async function generateRecoveryCodes(password: string): Promise<string[]> {
  const response = await ceApi("/api/auth/totp/recovery/generate", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to generate recovery codes"));
  }
  const data = (await response.json()) as { recovery_codes?: string[] };
  return data.recovery_codes ?? [];
}

export async function disableTotp(payload: {
  password: string;
  code?: string;
  recoveryCode?: string;
  stepUpToken?: string;
}): Promise<void> {
  const response = await ceApi("/api/auth/totp/disable", {
    method: "POST",
    body: JSON.stringify({
      password: payload.password,
      code: payload.code,
      recovery_code: payload.recoveryCode,
      step_up_token: payload.stepUpToken,
    }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to disable two-factor authentication"));
  }
}

export type AuthConfig = {
  auth_enabled: boolean;
  multi_user: boolean;
  otp_login_enabled?: boolean;
  otp_step_up_enabled?: boolean;
};

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const response = await ceApi("/api/auth/config");
  if (!response.ok) {
    throw new Error("Failed to load auth config");
  }
  return response.json() as Promise<AuthConfig>;
}

export async function sendEmailOtp(
  emailOrUsername: string | undefined,
  purpose: "login" | "step_up",
): Promise<{ challengeId: string; message: string }> {
  const response = await ceApi("/api/auth/otp/send", {
    method: "POST",
    body: JSON.stringify({
      email_or_username: emailOrUsername,
      purpose,
    }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to send verification code"));
  }
  const data = (await response.json()) as {
    challenge_id?: string;
    message?: string;
  };
  if (!data.challenge_id) {
    throw new Error(data.message || "If an account exists, a verification code was sent.");
  }
  return {
    challengeId: data.challenge_id,
    message: data.message || "If an account exists, a verification code was sent.",
  };
}

export async function verifyEmailOtpLogin(challengeId: string, code: string): Promise<CEUser> {
  const response = await ceApi("/api/auth/otp/verify", {
    method: "POST",
    body: JSON.stringify({ challenge_id: challengeId, code }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Invalid verification code"));
  }
  const data = (await response.json()) as { token: string; user: CEUser };
  setCESession(data.token, data.user);
  return data.user;
}

export async function verifyEmailOtpStepUp(challengeId: string, code: string): Promise<string> {
  const response = await ceApi("/api/auth/otp/verify", {
    method: "POST",
    body: JSON.stringify({ challenge_id: challengeId, code }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Invalid verification code"));
  }
  const data = (await response.json()) as { step_up_token?: string };
  if (!data.step_up_token) {
    throw new Error("Step-up verification failed");
  }
  return data.step_up_token;
}

export type SsoProvider = {
  name: string;
  display_name: string;
};

export type SsoLink = {
  provider: string;
  subject?: string;
  email?: string | null;
  linked_at?: number;
};

export async function fetchSsoProviders(): Promise<SsoProvider[]> {
  const response = await ceApi("/api/auth/sso/providers");
  if (!response.ok) {
    return [];
  }
  const data = (await response.json()) as { providers?: SsoProvider[] };
  return data.providers || [];
}

export async function fetchSsoLinks(): Promise<SsoLink[]> {
  const response = await ceApi("/api/auth/sso/links");
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to load connected accounts"));
  }
  const data = (await response.json()) as { links?: SsoLink[] };
  return data.links || [];
}

export function ssoStartUrl(provider: string, returnTo: string, mode: "login" | "link" = "login"): string {
  const base = getApiBaseUrl();
  const params = new URLSearchParams({
    return_to: returnTo,
    mode,
  });
  return `${base}/api/auth/sso/${encodeURIComponent(provider)}/start?${params.toString()}`;
}

export async function startSsoLink(provider: string, returnTo: string): Promise<string> {
  const response = await ceApi("/api/auth/sso/link", {
    method: "POST",
    body: JSON.stringify({ provider, return_to: returnTo }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to start account linking"));
  }
  const data = (await response.json()) as { start_url?: string };
  if (!data.start_url) {
    throw new Error("Missing link start URL");
  }
  const base = getApiBaseUrl();
  if (data.start_url.startsWith("http")) {
    return data.start_url;
  }
  return `${base}${data.start_url}`;
}

export async function unlinkSsoProvider(
  provider: string,
  options: { password?: string; stepUpToken?: string },
): Promise<void> {
  const response = await ceApi(`/api/auth/sso/link/${encodeURIComponent(provider)}`, {
    method: "DELETE",
    body: JSON.stringify({
      password: options.password,
      step_up_token: options.stepUpToken,
    }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to unlink provider"));
  }
}

export type ActiveSession = {
  session_id: string;
  device_label: string;
  ip_address_masked?: string | null;
  created_at?: number;
  last_seen_at?: number;
  is_current?: boolean;
};

export async function fetchActiveSessions(): Promise<ActiveSession[]> {
  const response = await ceApi("/api/auth/sessions");
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to load sessions"));
  }
  const data = (await response.json()) as {
    sessions?: ActiveSession[];
    newLoginBanner?: string | null;
  };
  if (typeof window !== "undefined" && data.newLoginBanner) {
    window.sessionStorage.setItem("keprix.newLoginBanner", data.newLoginBanner);
  }
  return data.sessions || [];
}

export async function revokeEverywhere(): Promise<{ removed: number }> {
  const response = await ceApi("/api/auth/sessions/revoke-everywhere", {
    method: "POST",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to revoke sessions"));
  }
  const data = (await response.json()) as { removed?: number };
  return { removed: data.removed ?? 0 };
}

export async function revokeActiveSession(sessionId: string): Promise<void> {
  const response = await ceApi(`/api/auth/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to revoke session"));
  }
}

export async function revokeOtherSessions(): Promise<{ removed: number }> {
  const response = await ceApi("/api/auth/sessions/revoke-others", {
    method: "POST",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(body, "Failed to revoke other sessions"));
  }
  const data = (await response.json()) as { removed?: number };
  return { removed: data.removed ?? 0 };
}
