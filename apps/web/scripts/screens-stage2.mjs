// Screenshots of the screens beyond the test flow (UPDATE_14 section 5): the creek check, the
// record, the two observers, the return check, the analyst's view, the judges' door and the
// poster, on the phone viewport (390 by 844), plus desktop for /, /city, /two and /judges.
// Against the fake API, so nothing is sent anywhere. Needs the production server on port 3100
// (npm run build && npm run start).
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, devices } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "..", "..", "..", "docs", "screens");
mkdirSync(out, { recursive: true });
const base = process.env.SCREENS_URL || "http://127.0.0.1:3100";
const content = JSON.parse(readFileSync(resolve(here, "..", "generated", "content.json"), "utf8"));
const firstWalk = (content.walks ?? [])[0];

const phone = [
  ["20-check-start", "/check"],
  ["21-spot-record", "/spot?id=example"],
  ["22-two", "/two"],
  ["23-quick", "/quick?spot=example"],
  ["24-city", "/city?creek=strawberry-creek"],
  ["25-judges", "/judges"],
  ["26-poster", "/poster"],
  ["27-walks", "/walk"],
  ...(firstWalk ? [["28-walk", `/walk/${firstWalk.id}`]] : []),
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

// A whole walk on a phone: the record made on the phone, then the demo creek it feeds.
async function walkThrough() {
  if (!firstWalk) return 0;
  const browser = await chromium.launch();
  const context = await browser.newContext({ ...devices["iPhone 13"], serviceWorkers: "block" });
  const page = await context.newPage();
  await mockApi(page);
  try {
    await page.goto(`${base}/walk/${firstWalk.id}`);
    await page.getByRole("button", { name: "Start the check" }).click();
    for (let i = 0; i < 40; i++) {
      if (await page.getByRole("heading", { name: "Your record from the clip" }).isVisible()) break;
      if (await page.getByRole("button", { name: "Finish" }).isVisible()) {
        await page.getByRole("button", { name: "Finish" }).click();
        continue;
      }
      // Each kind of question has its own way on: Skip, "None of these", a choice, or Next.
      const skip = page.getByRole("button", { name: "Skip" });
      const none = page.getByRole("button", { name: "None of these" });
      const choice = page.getByRole("main").getByRole("group").first().getByRole("button");
      if (await skip.first().isVisible()) await skip.first().click();
      else if (await none.isVisible()) await none.click();
      else if (await choice.first().isVisible()) await choice.first().click();
      else await page.getByRole("button", { name: "Next", exact: true }).click();
    }
    await page.getByRole("heading", { name: "Your record from the clip" }).waitFor();
    await page.screenshot({ path: join(out, "29-walk-record.png"), fullPage: true });
    console.log("screens: docs/screens/29-walk-record.png");
    await page.getByRole("link", { name: "See this creek as a city would" }).click();
    await page.getByRole("heading", { name: /Demo creek/ }).waitFor();
    await page.screenshot({ path: join(out, "29b-walk-city.png"), fullPage: true });
    console.log("screens: docs/screens/29b-walk-city.png");
    await browser.close();
    return 0;
  } catch (err) {
    console.log(`screens: the walk failed: ${String(err).split("\n")[0]}`);
    await browser.close();
    return 1;
  }
}

const failed =
  (await shoot(devices["iPhone 13"], phone)) +
  (await walkThrough()) +
  (await shoot({ viewport: { width: 1280, height: 800 } }, desktop));
process.exit(failed ? 1 : 0);
