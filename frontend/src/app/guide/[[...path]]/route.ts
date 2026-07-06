import { NextRequest, NextResponse } from "next/server";
import { readFileSync, existsSync, statSync } from "fs";
import { join, resolve } from "path";

const GUIDE_PUBLIC = join(process.cwd(), "public", "guide");

const MIME: Record<string, string> = {
  css: "text/css",
  js: "application/javascript",
  json: "application/json",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  svg: "image/svg+xml",
  ico: "image/x-icon",
  woff: "font/woff",
  woff2: "font/woff2",
  ttf: "font/ttf",
  gz: "application/gzip",
  xml: "application/xml",
  txt: "text/plain",
  webmanifest: "application/manifest+json",
};

function mimeFor(filePath: string): string {
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
  return MIME[ext] ?? "application/octet-stream";
}

export const runtime = "nodejs";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path = [] } = await context.params;

  // Guard against path traversal
  const resolved = resolve(join(GUIDE_PUBLIC, ...path));
  if (!resolved.startsWith(GUIDE_PUBLIC + "/") && resolved !== GUIDE_PUBLIC) {
    return new NextResponse("Forbidden", { status: 403 });
  }

  // Try exact path first, then index.html (MkDocs directory-style URLs)
  let filePath: string | null = null;
  for (const candidate of [resolved, join(resolved, "index.html")]) {
    if (existsSync(candidate) && statSync(candidate).isFile()) {
      filePath = candidate;
      break;
    }
  }

  if (!filePath) {
    return new NextResponse("Not found", { status: 404 });
  }

  const content = readFileSync(filePath);

  if (!filePath.endsWith(".html")) {
    return new NextResponse(content, {
      headers: { "Content-Type": mimeFor(filePath) },
    });
  }

  // Inject <base href="..."> so MkDocs relative paths (../../assets/) resolve correctly.
  // Treating the URL as a directory (adding trailing slash) makes ../../ climb to /guide/
  // instead of two levels above the URL's implicit parent.
  const html = content.toString("utf-8");
  const { pathname } = request.nextUrl;
  const baseHref = pathname.endsWith("/") ? pathname : pathname + "/";
  const patched = html.replace(/<head>/i, `<head><base href="${baseHref}">`);

  return new NextResponse(patched, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
