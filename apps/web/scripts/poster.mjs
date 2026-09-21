// Writes out/poster-letter.pdf and out/poster-a4.pdf from the /poster route with Playwright.
// Starts its own production server on port 3102 (builds first when no build exists).
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const port = Number(process.env.POSTER_PORT || 3102);
const out = join(webRoot, "out");

if (!existsSync(join(webRoot, ".next", "BUILD_ID"))) {
  console.log("poster: no build found, running npm run build first");
  const b = spawnSync("npm", ["run", "build"], { cwd: webRoot, stdio: "inherit" });
  if (b.status !== 0) process.exit(b.status ?? 1);
}

mkdirSync(out, { recursive: true });
const server = spawn("npx", ["next", "start", "-p", String(port)], { cwd: webRoot, stdio: ["ignore", "pipe", "pipe"] });
server.stderr.on("data", (d) => process.stderr.write(d));

async function waitFor(url, ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`server at ${url} did not answer in ${ms} ms`);
}

try {
  await waitFor(`http://127.0.0.1:${port}/poster`, 60000);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${port}/poster`, { waitUntil: "networkidle" });
  await page.emulateMedia({ media: "print" });
  for (const [name, format] of [
    ["poster-letter.pdf", "Letter"],
    ["poster-a4.pdf", "A4"],
  ]) {
    const path = join(out, name);
    await page.pdf({ path, format, printBackground: true, margin: { top: "0.5in", bottom: "0.5in", left: "0.5in", right: "0.5in" } });
    console.log(`poster: wrote ${path} (${statSync(path).size} bytes)`);
  }
  await browser.close();
} finally {
  server.kill("SIGTERM");
}
