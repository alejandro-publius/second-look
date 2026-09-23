// Two screenshots for the record: /city showing what the creek needs from the approved measures,
// and /spot showing the health card with one action each for the person, the pet and the city.
// Against the fake API, so the sentences are the approved ones and nothing is sent anywhere.
// Needs the production server on port 3100 (npm run build && npm run start).
import { mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, devices } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "..", "..", "..", "docs", "screens");
mkdirSync(out, { recursive: true });
const base = process.env.SCREENS_URL || "http://127.0.0.1:3100";

const browser = await chromium.launch();
const context = await browser.newContext({ ...devices["iPhone 13"], serviceWorkers: "block" });
const page = await context.newPage();
await mockApi(page);

await page.goto(`${base}/city?creek=strawberry-creek`);
await page.getByText("Find and fix leaking or wrongly connected sewers").waitFor();
await page.screenshot({ path: join(out, "10-city-needs.png"), fullPage: true });
console.log("screens: docs/screens/10-city-needs.png");

await page.goto(`${base}/spot?id=example`);
await page.getByRole("heading", { name: "What you can do" }).waitFor();
await page.screenshot({ path: join(out, "11-spot-health-card.png"), fullPage: true });
console.log("screens: docs/screens/11-spot-health-card.png");

await browser.close();
