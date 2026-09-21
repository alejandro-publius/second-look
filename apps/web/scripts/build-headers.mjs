// Writes public/_headers for Cloudflare Pages from security-headers.mjs, so the static export
// carries exactly the policy the server build sends. Runs as part of prebuild.
import { writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { headersFile } from "../security-headers.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const web = resolve(here, "..");
const apiOrigin = (process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");
const out = join(web, "public", "_headers");
writeFileSync(out, headersFile({ apiOrigin }));
console.log(`build-headers: wrote public/_headers for api origin ${apiOrigin}`);
