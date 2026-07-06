/** MkDocs site URLs served from Next.js public/guide by default. */

const DEFAULT_DOCS_BASE = "/guide";

export function getDocsBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_DOCS_URL?.replace(/\/$/, "");
  return configured || DEFAULT_DOCS_BASE;
}

export function isExternalDocsUrl(url: string): boolean {
  return /^https?:\/\//i.test(url);
}

export function docsPageUrl(path = ""): string {
  const base = getDocsBaseUrl().replace(/\/$/, "");
  if (!path) {
    return `${base}/`;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}${normalized.endsWith("/") ? "" : "/"}`;
}

export const DOCS_QUICKSTART_URL = docsPageUrl("getting-started/quickstart");
export const DOCS_HOME_URL = docsPageUrl();
