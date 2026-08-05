const STEP_UP_TOKEN_KEY = "keprix_step_up_token";

export function setStepUpToken(token: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STEP_UP_TOKEN_KEY, token);
}

export function getStepUpToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(STEP_UP_TOKEN_KEY);
}

export function clearStepUpToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STEP_UP_TOKEN_KEY);
}
