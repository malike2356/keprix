import type { NextConfig } from "next";

// Server-side rewrite target (Docker internal hostname or localhost).
// Keep NEXT_PUBLIC_* empty in production so the browser uses same-origin /api.
const backendBase =
  process.env.BACKEND_REWRITE_URL ||
  process.env.NEXT_PUBLIC_CE_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:3333";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  async redirects() {
    return [
      { source: "/rag-pipeline", destination: "/data?tab=rag", permanent: false },
      { source: "/playbook", destination: "/data?tab=models", permanent: false },
      { source: "/ingest/video", destination: "/data?tab=video", permanent: false },
      { source: "/usage", destination: "/data?tab=usage", permanent: false },
      { source: "/observability", destination: "/data?tab=observability", permanent: false },
    ];
  },
  async rewrites() {
    const base = backendBase.replace(/\/$/, "");
    return [
      {
        source: "/openapi.json",
        destination: `${base}/openapi.json`,
      },
      {
        source: "/api/:path*",
        destination: `${base}/api/:path*`,
      },
      {
        source: "/sidecar/:path*",
        destination: `${base}/sidecar/:path*`,
      },
      {
        source: "/v1/products/:path*",
        destination: `${base}/v1/products/:path*`,
      },
      {
        source: "/carina/:path*",
        destination: `${base}/carina/:path*`,
      },
      { source: "/admin", destination: "/dashboard" },
      { source: "/admin/dashboard", destination: "/dashboard" },
      { source: "/admin/:path*", destination: "/dashboard/:path*" },
    ];
  },
};

export default nextConfig;
