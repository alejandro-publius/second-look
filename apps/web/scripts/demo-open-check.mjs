// Is judge mode open on the live site? First asked by UPDATE_27 for Sep 28, a dated item in
// docs/internal/DONE.md; since UPDATE_33 judge mode is shut again until the second lock,
// 2026-10-03T04:00:00Z, because a second wave of the study runs until then.
//
// Judge mode is shut until that lock and the page decides by the browser's own clock, so this
// loads the live page in Chromium and reads its first heading. Every request that is not GET,
// HEAD or OPTIONS is aborted before it leaves the browser, so this can never write to production
// or start a study session. Exit 0 when the page shows judge mode open, 1 when it shows it shut
// or anything else. With --expect shut it is the other way round: exit 0 only when the page
// shows judge mode shut, which is the check to run after the deploy that shuts it.
//
//   node scripts/demo-open-check.mjs
//   node scripts/demo-open-check.mjs --expect shut
//   DEMO_URL=https://second-look-79t.pages.dev/t2/demo node scripts/demo-open-check.mjs
//   DEMO_URL=http://localhost:3100/demo node scripts/demo-open-check.mjs
//   node scripts/demo-open-check.mjs --clock 2026-10-04T00:00:00Z   pretend it is that time,
//     to test this script before the date; make done-check never passes it.
import { readFileSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const WORDS = join(here, "..", "..", "..", "content", "locales", "en.json");

/** The value after a flag on the command line, or null. */
export function flag(argv, name) {
  const at = argv.indexOf(name);
  return at > 0 && at + 1 < argv.length ? argv[at + 1] : null;
}

/**
 * What the heading a judge mode page shows means. Both pages share the shut heading; /demo and
 * /t2/demo each have their own open one. pass is true only when the page shows what was
 * expected, "open" or "shut"; any other heading is not the judge mode page and never passes.
 */
export function verdict(heading, url, expect, words) {
  if (expect !== "open" && expect !== "shut") throw new Error(`--expect takes open or shut, not ${expect}`);
  const part2 = new URL(url).pathname.replace(/\/$/, "").endsWith("/t2/demo");
  const openHeading = String(words[part2 ? "part2.demo_title" : "demo.title"]);
  const shutHeading = String(words["demo.shut_title"]);
  const state = heading === openHeading ? "open" : heading === shutHeading ? "shut" : "other";
  const said = { open: "judge mode is open", shut: expect === "shut" ? "judge mode is shut" : "judge mode is still shut", other: "not the judge mode page" }[state];
  return { state, pass: state === expect, said };
}

async function main() {
  const words = JSON.parse(readFileSync(WORDS, "utf8"));
  const url = process.env.DEMO_URL ?? "https://second-look-79t.pages.dev/demo";
  const clock = flag(process.argv, "--clock");
  const expect = flag(process.argv, "--expect") ?? "open";
  verdict("", url, expect, words); // a wrong --expect stops here, before any browser opens

  const { chromium } = await import("@playwright/test");
  const browser = await chromium.launch();
  const blocked = [];
  let heading = "";
  let answered = true;
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await page.route("**/*", (route) => {
      const method = route.request().method();
      if (["GET", "HEAD", "OPTIONS"].includes(method)) return route.continue();
      blocked.push(`${method} ${route.request().url()}`);
      return route.abort();
    });
    if (clock) await page.clock.install({ time: new Date(clock) });
    const response = await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
    if (!response || response.status() !== 200) {
      console.log(`demo-open-check: ${url} answered ${response ? response.status() : "nothing"}`);
      answered = false;
    } else {
      await page.waitForFunction(() => document.querySelector("h1")?.textContent?.trim(), null, { timeout: 15000 });
      heading = (await page.locator("h1").first().textContent())?.trim() ?? "";
    }
  } finally {
    await browser.close();
  }
  if (blocked.length) console.log(`demo-open-check: aborted before sending: ${blocked.join(", ")}`);
  if (!answered) {
    process.exitCode = 1;
    return;
  }
  const result = verdict(heading, url, expect, words);
  console.log(`demo-open-check: ${url} shows "${heading}", ${result.said}${result.pass ? "" : `, expected ${expect}`}`);
  if (!result.pass) process.exitCode = 1;
}

// Run only as a script, so a test can import the helpers above without opening a browser.
if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) await main();
