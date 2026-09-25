// Part 2 on the deployed site, on a phone viewport, against the real API (UPDATE_31 section 3):
// one sitting in each arm, the assisted one with a Keep and a Change. Every sitting is marked
// is_test by the x-qa-key header, and a QA check names its part 2 arm, so it takes no slot from
// the real sequence. The public counts are read before and after, and the run fails if any real
// count moved. Writes results/part2_live_check.json.
//
//   SITE_URL=https://second-look-79t.pages.dev QA_KEY=... node apps/web/scripts/live-part2.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { chromium } from "@playwright/test";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..", "..");
const site = (process.env.SITE_URL ?? "").replace(/\/$/, "");
const api = (process.env.API_URL ?? site).replace(/\/$/, "");
const qaKey = process.env.QA_KEY;
if (!site) throw new Error("set SITE_URL");
if (!qaKey) throw new Error("set QA_KEY to the Worker's QA_KEY secret; without it the sittings would be stored as real");

// The committed flags, to pick answers that make the question appear. The browser never gets them.
const CONTENT = JSON.parse(readFileSync(join(root, "worker", "src", "content.json"), "utf8"));
const FLAGS = CONTENT.part2_flags;
const flagged = Object.keys(FLAGS).filter((id) => FLAGS[id] !== null);
if (flagged.length < 2) throw new Error(`need two flagged items for a Keep and a Change, the committed flags have ${flagged.length}`);
const disagree = (side) => (side === "present" ? "No" : "Yes");
const QUESTION = "The checker noticed something here. Look again?";

const headers = { "content-type": "application/json", "x-qa-key": qaKey };
async function call(method, path, body) {
  const r = await fetch(`${api}${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new Error(`${method} ${path}: ${r.status} ${JSON.stringify(data)}`);
  return data;
}
async function realCounts() {
  const [a, b] = await Promise.all([fetch(`${api}/api/test/counts`).then((r) => r.json()), fetch(`${api}/api/t2/counts`).then((r) => r.json())]);
  return JSON.stringify({ part1: a.by_arm, part2: b });
}

/** Part 1 through the API, marked as a test, finished to its score. */
async function part1() {
  const s = await call("POST", "/api/test/session", {
    consent_version: "live-check", content_hash: CONTENT.content_hash, build_hash: "live-part2", source_label: "other", hidden_field: "",
    client_token_hash: `live-part2-${Math.random().toString(16).slice(2)}-0123456789`, ua_class: "phone",
  });
  let position = 0;
  for (const id of s.item_order) await call("POST", "/api/test/response", { session_id: s.session_id, item_id: id, answer: "cant_tell", rt_ms: 900, position: position++ });
  await call("POST", "/api/test/complete", { session_id: s.session_id, prior_experience: "no", answered_count: 16 });
  return s.session_id;
}

const before = await realCounts();
const browser = await chromium.launch();
const out = { site, ran_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"), commit: execFileSync("git", ["rev-parse", "--short", "HEAD"], { cwd: root }).toString().trim(), arms: [], choices: [], scores: {}, ok: false };

try {
  for (const arm of ["assisted", "unassisted"]) {
    const sessionId = await part1();
    // The arm is named before the page asks, so the page's own offer finds this second look.
    await call("POST", "/api/t2/offer", { session_id: sessionId, decision: "start", qa_arm: arm });
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, serviceWorkers: "block", extraHTTPHeaders: { "x-qa-key": qaKey } });
    await context.addInitScript((sid) => localStorage.setItem("sl_open_session", JSON.stringify({ session_id: sid })), sessionId);
    const page = await context.newPage();
    // The real path: part 1's score screen, its offer card, Start.
    await page.goto(`${site}/t`);
    await page.getByTestId("part2-offer").waitFor({ timeout: 30_000 });
    await page.getByRole("button", { name: "Start the second look" }).click();
    await page.getByRole("button", { name: "Start", exact: true }).click();
    let asked = 0;
    for (let n = 1; n <= 8; n++) {
      await page.getByText(`Photo ${n} of 8`).waitFor({ timeout: 30_000 });
      // Which item is on screen is not shown; the server's order says.
      const state = await call("GET", `/api/t2/resume?part2_id=${encodeURIComponent(JSON.parse(await page.evaluate(() => localStorage.getItem("sl_open_part2"))).part2_id)}`);
      const id = state.item_order[n - 1];
      const answer = FLAGS[id] ? disagree(FLAGS[id]) : "Can't tell";
      await page.getByRole("button", { name: answer, exact: true }).click();
      await page.locator("[data-confirm]").click();
      const question = page.getByText(QUESTION);
      const shown = await question.waitFor({ timeout: 8_000 }).then(() => true, () => false);
      if (shown !== (arm === "assisted" && FLAGS[id] !== null)) throw new Error(`${arm} ${id}: question shown ${shown}`);
      if (shown) {
        asked += 1;
        if (asked === 1) {
          await page.getByRole("button", { name: "Keep", exact: true }).click();
          out.choices.push("keep");
        } else {
          await page.getByRole("button", { name: "Change", exact: true }).click();
          await page.getByRole("button", { name: answer === "Yes" ? "No" : "Yes", exact: true }).click();
          await page.locator("[data-confirm]").click();
          out.choices.push("change");
        }
      }
    }
    await page.getByTestId("part2-score").waitFor({ timeout: 30_000 });
    out.scores[arm] = await page.getByTestId("part2-score").innerText();
    out.arms.push(arm);
    console.log(`live part 2: ${arm}, ${asked} question(s), score "${out.scores[arm]}"`);
    await context.close();
  }
  const after = await realCounts();
  if (after !== before) throw new Error(`a real count moved: before ${before}, after ${after}`);
  out.ok = true;
} finally {
  await browser.close();
  writeFileSync(join(root, "results", "part2_live_check.json"), JSON.stringify(out, null, 2) + "\n");
}
console.log(`live part 2: both arms passed, choices ${out.choices.join(" and ")}, real counts unchanged`);
