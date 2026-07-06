import type { NextConfig } from "next";

const backendBase =
  process.env.NEXT_PUBLIC_CE_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:3333";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
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
      { source: "/admin", destination: "/dashboard" },
      { source: "/admin/dashboard", destination: "/dashboard" },
      { source: "/admin/:path*", destination: "/dashboard/:path*" },
    ];
  },
};

export default nextConfig;
