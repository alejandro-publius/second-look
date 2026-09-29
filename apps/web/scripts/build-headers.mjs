// Writes public/_headers for Cloudflare Pages from security-headers.mjs, so the static export
// carries exactly the policy the server build sends. Runs as part of prebuild.
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { headersFile, isLocalOrigin, photoPreloads } from "../security-headers.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const web = resolve(here, "..");
const asked = (process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");
// public/_headers is tracked, and Cloudflare Pages is the only server that reads it. A build
// whose API is on this machine is a test or development build: its own server sends the policy
// from next.config.ts, with the local address in it. So for such a build the file keeps the
// policy production sends, own origin only, and the tracked copy stays as it was committed.
const local = isLocalOrigin(asked);
const apiOrigin = local ? "" : asked;
const out = join(web, "public", "_headers");
// build-content.mjs runs first in prebuild and export, so the content file is there to read.
const contentPath = join(web, "generated", "content.json");
const preloads = existsSync(contentPath) ? photoPreloads(JSON.parse(readFileSync(contentPath, "utf8"))) : {};
writeFileSync(out, headersFile({ apiOrigin, preloads }));
const policy = apiOrigin ? `api origin ${apiOrigin}` : local ? `this site's own origin only (${asked} is local, so this build's server sends its own policy)` : "this site's own origin only";
console.log(`build-headers: wrote public/_headers for ${policy}, photo preloads on ${Object.keys(preloads).join(" and ") || "no page"}`);
