/** Hosts where `/` is the operator workspace, not the public marketing homepage. */

export function isWorkspaceEntryHost(hostHeader: string): boolean {
  const host = hostHeader.split(":")[0].toLowerCase().replace(/^\[|\]$/g, "");
  if (host === "localhost" || host === "127.0.0.1" || host === "::1") return true;
  if (host === "app.keprixai.com") return true;
  if (host.endsWith(".localhost")) return true;
  return false;
}
