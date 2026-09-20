import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { isWorkspaceEntryHost } from "@/lib/workspace-entry-host";

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname !== "/") return NextResponse.next();
  const host = request.headers.get("host") || "";
  if (!isWorkspaceEntryHost(host)) return NextResponse.next();
  const url = request.nextUrl.clone();
  url.pathname = "/home";
  return NextResponse.redirect(url);
}

export const config = {
  matcher: [
    // matcher: "/" compiles to an /index pattern and never runs on the homepage.
    "/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)",
  ],
};
