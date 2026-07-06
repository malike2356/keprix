export const MICROPHONE_BLOCKED_MESSAGE =
  "Microphone blocked. Allow mic access in browser settings.";

export async function checkMicrophonePermission(): Promise<PermissionState | "unsupported"> {
  if (typeof navigator === "undefined" || !navigator.permissions?.query) {
    return "unsupported";
  }
  try {
    const result = await navigator.permissions.query({ name: "microphone" as PermissionName });
    return result.state;
  } catch {
    return "unsupported";
  }
}

export function mapMicrophoneError(error: unknown): string {
  const name = error instanceof DOMException ? error.name : "";

  if (name === "NotAllowedError" || name === "SecurityError") {
    return MICROPHONE_BLOCKED_MESSAGE;
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return "No microphone was found on this device.";
  }
  if (name === "NotReadableError" || name === "TrackStartError") {
    return "Microphone is in use by another application.";
  }
  if (name === "OverconstrainedError") {
    return "Microphone constraints are not supported in this browser.";
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "Could not start microphone recording.";
}
