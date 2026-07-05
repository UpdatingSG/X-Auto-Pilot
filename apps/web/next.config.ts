import type { NextConfig } from "next";

/** Server-side API target for Vercel rewrites (set API_URL on Vercel). */
const apiUrl =
  process.env.API_URL?.replace(/\/$/, "") ??
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/v1/:path*",
        destination: `${apiUrl}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
