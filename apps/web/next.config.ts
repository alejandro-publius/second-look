import type { NextConfig } from "next";
import { buildHeaders } from "./security-headers.mjs";

// The API origin is the only place the browser may connect to besides our own origin.
const apiOrigin = (process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");
const isDev = process.env.NODE_ENV === "development";

// One definition, shared with scripts/build-headers.mjs, which writes public/_headers for
// Cloudflare Pages. A static export gets no headers from Next, so the two must not drift.
const { everywhere, fieldPermissions } = buildHeaders({ apiOrigin, isDev });

// NEXT_EXPORT=1 builds the static site Cloudflare Pages serves. The default stays standalone so
// docker compose, `next start` and the Playwright suite keep working exactly as before.
const isExport = process.env.NEXT_EXPORT === "1";

const nextConfig: NextConfig = {
  output: isExport ? "export" : "standalone",
  poweredByHeader: false,
  // A static export serves no headers of its own, so the same policy lives in public/_headers,
  // which Cloudflare Pages reads. scripts/check_headers.mjs proves the two say the same thing.
  ...(isExport
    ? {}
    : {
        async headers() {
          return [
            { source: "/:path*", headers: everywhere },
            { source: "/check", headers: [fieldPermissions] },
            { source: "/quick", headers: [fieldPermissions] },
            { source: "/sw.js", headers: [{ key: "Cache-Control", value: "no-cache" }] },
          ];
        },
      }),
};

export default nextConfig;
