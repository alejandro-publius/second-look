// Screenshots of the screens beyond the test flow (UPDATE_14 section 5): the creek check, the
// record, the two observers, the return check, the analyst's view, the judges' door and the
// poster, on the phone viewport (390 by 844), plus desktop for /, /city, /two and /judges.
// Against the fake API, so nothing is sent anywhere. Needs the production server on port 3100
// (npm run build && npm run start).
import { mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, devices } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "..", "..", "..", "docs", "screens");
mkdirSync(out, { recursive: true });
const base = process.env.SCREENS_URL || "http://127.0.0.1:3100";

const phone = [
  ["20-check-start", "/check"],
  ["21-spot-record", "/spot?id=example"],
  ["22-two", "/two"],
  ["23-quick", "/quick?spot=example"],
  ["24-city", "/city?creek=strawberry-creek"],
  ["25-judges", "/judges"],
  ["26-poster", "/poster"],
];
const desktop = [
  ["30-landing-desktop", "/"],
  ["31-city-desktop", "/city?creek=strawberry-creek"],
  ["32-two-desktop", "/two"],
  ["33-judges-desktop", "/judges"],
];

async function shoot(contextOptions, list) {
  const browser = await chromium.launch();
  const context = await browser.newContext({ ...contextOptions, serviceWorkers: "block" });
  const page = await context.newPage();
  await mockApi(page);
  let failed = 0;
  for (const [name, path] of list) {
    try {
      await page.goto(`${base}${path}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(500);
      const file = join(out, `${name}.png`);
      await page.screenshot({ path: file, fullPage: true });
      console.log(`screens: docs/screens/${name}.png`);
    } catch (err) {
      failed++;
      console.log(`screens: ${name} failed: ${String(err).split("\n")[0]}`);
    }
  }
  await browser.close();
  return failed;
}

const failed =
  (await shoot(devices["iPhone 13"], phone)) +
  (await shoot({ viewport: { width: 1280, height: 800 } }, desktop));
process.exit(failed ? 1 : 0);
