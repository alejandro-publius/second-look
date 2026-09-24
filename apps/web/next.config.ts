import { join } from "node:path";
import type { NextConfig } from "next";
import { buildHeaders } from "./security-headers.mjs";

// The API origin is the only place the browser may connect to besides our own origin.
const apiOrigin = (process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");
const isDev = process.env.NODE_ENV === "development";

// One definition, shared with scripts/build-headers.mjs, which writes public/_headers for
// Cloudflare Pages. A static export gets no headers from Next, so the two must not drift.
const { everywhere, fieldPermissions } = buildHeaders({ apiOrigin, isDev });

// NEXT_EXPORT=1 builds the static site Cloudflare Pages serves. The default stays standalone for
// docker compose. `next start` and the Playwright suite serve .next itself, not the standalone copy.
const isExport = process.env.NEXT_EXPORT === "1";

// The repository root, so the web app can import the Worker's pure core (worker/src/core), the
// same functions the golden vectors prove equal to Python. The video walks build their record
// with it on the device. Next sets the tracing root and the Turbopack root to one value, so both
// are the repo root, and that moves the standalone server: it is .next/standalone/apps/web/server.js,
// not .next/standalone/server.js. apps/web/Dockerfile copies worker/src/core and runs that path.
const repoRoot = join(__dirname, "..", "..");

const nextConfig: NextConfig = {
  output: isExport ? "export" : "standalone",
  turbopack: { root: repoRoot },
  outputFileTracingRoot: repoRoot,
  poweredByHeader: false,
  // next dev writes a block into AGENTS.md and CLAUDE.md when it thinks an AI agent runs it. The
  // block has an em dash, which dash-check refuses, and it dirties two tracked files on every run.
  agentRules: false,
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
