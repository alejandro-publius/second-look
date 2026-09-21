import type { NextConfig } from "next";

// The API origin is the only place the browser may connect to besides our own origin.
const apiOrigin = (process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");
const isDev = process.env.NODE_ENV === "development";

// Content-Security-Policy. Next.js App Router hydrates through inline <script> tags it writes
// itself, so script-src needs 'unsafe-inline'; a nonce would force every page to render per
// request and the landing page must stay static. 'unsafe-eval' is only added in development,
// where React uses eval for error stacks. Styles come from our own CSS files only.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  `style-src 'self'${isDev ? " 'unsafe-inline'" : ""}`,
  "img-src 'self' data: blob:",
  `connect-src 'self' ${apiOrigin}`,
  "font-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "manifest-src 'self'",
  "worker-src 'self'",
].join("; ");

const everywhere = [
  { key: "Content-Security-Policy", value: csp },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "geolocation=(), camera=(), microphone=(), payment=(), usb=()" },
];

// Only the creek check and the quick return check ask for location or a camera photo.
const fieldPermissions = { key: "Permissions-Policy", value: "geolocation=(self), camera=(self), microphone=(), payment=(), usb=()" };

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [
      { source: "/:path*", headers: everywhere },
      { source: "/check", headers: [fieldPermissions] },
      { source: "/quick/:spot", headers: [fieldPermissions] },
      { source: "/sw.js", headers: [{ key: "Cache-Control", value: "no-cache" }] },
    ];
  },
};

export default nextConfig;
