import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { anchorFor, hashedText, headsAgainstLog, parseLog, sha256Hex, verifyChain, type AuditEntry, type OtsProof } from "../lib/chain";
import { anchorText, logStampDay, proofName, proofStatus } from "../lib/verify-text";
import { assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

// /verify (UPDATE_29 section 3): each line of the audit log with its receipt and its place in the
// chain, the chain checked in the browser by the rule in lib/chain.ts, and the OpenTimestamps
// status from results/ots.json, after a plain sentence on what OpenTimestamps is.
const REPO = join(__dirname, "..", "..", "..");
const log: AuditEntry[] = parseLog(readFileSync(join(REPO, "audit", "log.jsonl"), "utf8"));
const ots: { proofs: OtsProof[] } = JSON.parse(readFileSync(join(REPO, "results", "ots.json"), "utf8"));

test("verify: the browser checks the chain and shows every receipt in order", async ({ page }) => {
  const urls = watchRequests(page);
  const csp: string[] = [];
  page.on("console", (m) => {
    if (m.text().includes("Content Security Policy")) csp.push(m.text());
  });
  await mockApi(page);
  await page.goto("/verify");
  await expect(page.getByRole("heading", { level: 1, name: "Check our records" })).toBeVisible();
  const status = page.getByTestId("chain-status");
  await expect(status).toHaveAttribute("data-checked", "browser");
  await expect(status).toHaveText(`The chain holds. Your browser just checked all ${log.length} lines, and each receipt matches its line and the line before it.`);
  for (const e of log) {
    const line = page.locator(`#line-${e.seq}`);
    await expect(line.getByRole("heading", { name: `Line ${e.seq} of ${log.length}` })).toBeVisible();
    await expect(page.getByTestId(`receipt-${e.seq}`)).toHaveText(e.hash);
  }
  await expect(page.locator("body")).not.toContainText("[missing:");
  // Checked here, on this machine: the page asks nothing of any other origin to do it.
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
  expect(csp).toEqual([]);
});

test("verify: says what OpenTimestamps is, and shows each proof's status from results/ots.json", async ({ page }) => {
  await mockApi(page);
  await page.goto("/verify");
  await expect(page.getByText("OpenTimestamps is a public timestamp service. It is not ours, and it is not our own chain.", { exact: false })).toBeVisible();
  // Hard rule 20: ours is an audit log. The one mention of a blockchain says it is not one.
  const text = await page.locator("main").innerText();
  expect(text.match(/blockchain/gi) ?? []).toHaveLength(1);
  expect(text).toContain("This is an audit log, not a blockchain.");
  // CRITIC_10 S02: a day with no new line gets no new stamp (scripts/anchor_audit_head.py), so the
  // page does not say the log is stamped every day.
  expect(text).toContain("Once a day we stamp the audit log's last receipt, if it has changed since the last stamp.");
  expect(text).not.toContain("once a day, which");
  for (const what of ["prereg_tag", "analysis_plan", "prereg_tag_v2", "analysis_plan_v2"]) {
    const p = ots.proofs.find((x) => x.what === what);
    expect(p, `results/ots.json has no ${what} proof`).toBeTruthy();
    const card = page.getByTestId(`proof-${what}`);
    if (p!.status === "confirmed") await expect(card).toContainText(`Confirmed in Bitcoin block ${p!.bitcoin!.block_height}`);
    else if (p!.status === "pending") await expect(card).toContainText("Waiting for a Bitcoin block.");
    await expect(card).toContainText(p!.proof);
  }
  // The newest audit head proof covers the last line, and the line says how far it has got.
  const last = log[log.length - 1];
  const anchor = anchorFor(last.seq, log, ots.proofs);
  expect(anchor, "no audit head proof covers the last line of the audit log").not.toBeNull();
  const shown = page.getByTestId(`anchor-${last.seq}`);
  if (anchor!.status === "confirmed") await expect(shown).toContainText(`In Bitcoin block ${anchor!.bitcoin!.block_height}`);
  else await expect(shown).toContainText("Waiting for a Bitcoin block.");
  // The committed log still has the line each audit head proof stamped, so none shows as broken.
  await expect(page.getByTestId("proof-audit_head").first()).toBeVisible();
  await expect(page.getByTestId("proof-audit_head").filter({ hasText: "This proof does not match its file." })).toHaveCount(0);
  await expect(page.getByText("uv run ots verify proofs/prereg-v1.tag.ots")).toBeVisible();
});

test("verify: a receipt from the address finds its line, and an unknown one says so", async ({ page }) => {
  await mockApi(page);
  const second = log[1] ?? log[0];
  await page.goto(`/verify?receipt=${second.hash.toUpperCase()}`);
  await expect(page.getByTestId("lookup-result")).toContainText(`Found. This receipt belongs to line ${second.seq} of ${log.length}.`);
  await expect(page.locator(`#line-${second.seq}`)).toHaveAttribute("aria-current", "true");
  await expect(page.locator('[aria-current="true"]')).toHaveCount(1);

  await page.goto(`/verify?receipt=${"ab".repeat(32)}`);
  await expect(page.getByTestId("lookup-result")).toHaveText("No line in the audit log has this receipt.");
  await expect(page.locator('[aria-current="true"]')).toHaveCount(0);

  // The form is a plain GET to this page, so it works the same way.
  await page.goto("/verify");
  await page.getByLabel("Look up a receipt").fill(log[0].payload_sha256);
  await page.getByRole("button", { name: "Find it" }).click();
  await expect(page).toHaveURL(new RegExp(`/verify\\?receipt=${log[0].payload_sha256}$`));
  await expect(page.getByTestId("lookup-result")).toContainText(`This is the hash of what line 1 of ${log.length} recorded.`);
});

test("verify: fits a phone and has no serious accessibility problem", async ({ page }) => {
  await mockApi(page);
  await page.goto("/verify");
  await expect(page.getByTestId("chain-status")).toHaveAttribute("data-checked", "browser");
  const { scroll, viewport } = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: window.innerWidth }));
  expect(scroll).toBeLessThanOrEqual(viewport);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
});

// The rule itself, run here in Node with the same Web Crypto the browser uses.
test("chain rule: the committed log holds, and each kind of tampering breaks it at its line", async () => {
  const ok = await verifyChain(log);
  expect(ok).toEqual({ ok: true, length: log.length, last: log[log.length - 1].hash });
  const copy = () => log.map((e) => ({ ...e }));

  const edited = copy();
  edited[0].ts_utc = "2026-09-20T00:00:00Z";
  expect(await verifyChain(edited)).toEqual({ ok: false, line: 1, reason: "hash" });

  const kind = copy();
  kind[1].kind = "test_only";
  expect(await verifyChain(kind)).toEqual({ ok: false, line: 2, reason: "kind" });

  const missing = copy();
  missing.splice(1, 1);
  expect(await verifyChain(missing)).toEqual({ ok: false, line: 2, reason: "seq" });

  // A line rewritten with a fresh, self-consistent hash still breaks the next line's link.
  const relinked = copy();
  relinked[0].payload_sha256 = "0".repeat(64);
  relinked[0].hash = await sha256Hex(hashedText(relinked[0]));
  expect(await verifyChain(relinked)).toEqual({ ok: false, line: 2, reason: "prev" });
});

test("chain rule: a timestamp proof covers a line only when it stamped this chain's hash", () => {
  const head: OtsProof = { proof: "proofs/audit-head-2026-09-24.ots", what: "audit_head", status: "pending", audit_seq: log.length, file_sha256: log[log.length - 1].hash };
  expect(anchorFor(1, log, [head])).toBe(head);
  expect(anchorFor(log.length, log, [head])).toBe(head);
  expect(anchorFor(1, log, [{ ...head, file_sha256: "cd".repeat(32) }])).toBeNull();
  // A proof of an earlier line covers that line and those before it, never a later one.
  const earlier: OtsProof = { ...head, audit_seq: log.length - 1, file_sha256: log[log.length - 2].hash };
  expect(anchorFor(log.length - 1, log, [earlier])).toBe(earlier);
  expect(anchorFor(log.length, log, [earlier])).toBeNull();
  const confirmed: OtsProof = { ...head, proof: "proofs/audit-head-2026-09-25.ots", status: "confirmed", bitcoin: { block_height: 915000 } };
  expect(anchorFor(1, log, [head, confirmed])).toBe(confirmed);
  // A checked block beats an unchecked one, even an earlier one.
  const unchecked: OtsProof = { ...head, proof: "proofs/audit-head-2026-09-26.ots", status: "unchecked", bitcoin: { block_height: 914000 } };
  expect(anchorFor(1, log, [unchecked, confirmed])).toBe(confirmed);
  expect(anchorFor(1, log, [{ ...head, status: "broken" }])).toBeNull();
});

test("chain rule: a stamp of a line this log no longer has shows as broken", async () => {
  const last = log[log.length - 1];
  const head: OtsProof = { proof: "proofs/audit-head-2026-09-24.ots", what: "audit_head", status: "pending", audit_seq: last.seq, file_sha256: last.hash };
  const plan: OtsProof = { proof: "proofs/prereg-v1.tag.ots", what: "prereg_tag", status: "pending" };
  expect(headsAgainstLog([plan, head], log)).toEqual([head]);
  // Line added later: the stamped line is still there, so the stamp still counts.
  const longer = [...log, { ...last, seq: last.seq + 1, prev_hash: last.hash, hash: "ef".repeat(32) }];
  expect(headsAgainstLog([head], longer)).toEqual([head]);

  // The stamped line rewritten with a fresh hash: the chain holds on its own, so only the stamp
  // can tell, and results/ots.json may not have caught up with the log.
  const rewritten = log.map((e) => ({ ...e }));
  rewritten[rewritten.length - 1].payload_sha256 = "0".repeat(64);
  rewritten[rewritten.length - 1].hash = await sha256Hex(hashedText(rewritten[rewritten.length - 1]));
  expect((await verifyChain(rewritten)).ok).toBe(true);
  const shown = headsAgainstLog([plan, head], rewritten);
  expect(shown).toEqual([{ ...head, status: "broken" }]);
  expect(proofStatus(shown[0])).toBe("This proof does not match its file.");
  expect(anchorFor(last.seq, rewritten, shown)).toBeNull();

  // Cut short, past the stamped line.
  expect(headsAgainstLog([head], log.slice(0, -1))[0].status).toBe("broken");
});

test("status words: every OpenTimestamps status, including those the committed file has not reached", () => {
  const base: OtsProof = { proof: "proofs/prereg-v1.tag.ots", what: "prereg_tag", status: "pending" };
  const block = { block_height: 915000, block_time_utc: "2026-09-24T21:46:40Z" };
  expect(proofName(base)).toBe("The tag prereg-v1, which fixes the analysis plan in git");
  expect(proofName({ ...base, what: "audit_head", audit_seq: 3 })).toBe("The audit log up to line 3");
  expect(proofStatus(base)).toBe("Waiting for a Bitcoin block. That takes a few hours after a stamp.");
  expect(proofStatus({ ...base, status: "confirmed", bitcoin: block })).toBe("Confirmed in Bitcoin block 915000, 2026-09-24.");
  expect(proofStatus({ ...base, status: "unchecked", bitcoin: block })).toBe("Named in Bitcoin block 915000, not checked yet.");
  expect(proofStatus({ ...base, status: "broken", bitcoin: block })).toBe("This proof does not match its file.");
  const head: OtsProof = { proof: "proofs/audit-head-2026-09-24.ots", what: "audit_head", status: "pending", audit_seq: 3 };
  expect(anchorText(null)).toBe("Not stamped yet.");
  expect(anchorText(head)).toBe("Stamped on 2026-09-24. Waiting for a Bitcoin block.");
  expect(anchorText({ ...head, status: "confirmed", bitcoin: block })).toBe("In Bitcoin block 915000, 2026-09-24.");
  expect(anchorText({ ...head, status: "unchecked", bitcoin: block })).toBe("Named in Bitcoin block 915000, not checked yet.");
});

// CRITIC_09 Q03: /judges said /verify proves no line was changed after it was written, but the
// only stamps came days after the lines. A stamp shows each line as it was on the day of the
// stamp. The door now says no line has changed since that day, read from the log and
// results/ots.json, and /verify says what a stamp does not show.
test("the judges' door and /verify say a stamp covers the lines from its own day, not from when they were written", async ({ page }) => {
  const en: Record<string, string> = JSON.parse(readFileSync(join(REPO, "content", "locales", "en.json"), "utf8"));
  const last = log[log.length - 1];
  const head = headsAgainstLog(ots.proofs, log).find((p) => p.status === "confirmed" && (p.audit_seq ?? 0) >= last.seq);
  // A line written after the newest confirmed stamp (the daily anchor stamps it, and a block
  // confirms it hours later): then there is no day to name, and the door says so.
  const day = head ? new Date(head.bitcoin!.block_time_utc!).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" }) : null;
  expect(logStampDay(log, ots.proofs)).toBe(day);
  // A line after the last stamp, a stamp still waiting for its block, or no stamp: no day to name.
  const extra: AuditEntry = { ...last, seq: last.seq + 1, prev_hash: last.hash, hash: "f".repeat(64) };
  expect(logStampDay([...log, extra], ots.proofs)).toBeNull();
  expect(logStampDay(log, ots.proofs.map((p) => ({ ...p, status: "pending" as const })))).toBeNull();
  expect(logStampDay(log, [])).toBeNull();

  await mockApi(page);
  await page.goto("/judges");
  const door = page.locator(".row").filter({ has: page.getByRole("link", { name: en["judges.verify"], exact: true }) });
  await expect(door.locator(".row-value")).toHaveText(day ? en["judges.verify_note"].replace("{date}", day) : en["judges.verify_note_unstamped"]);
  await expect(door).not.toContainText("after it was written");
  await page.goto("/verify");
  await expect(page.getByTestId("stamp-day")).toHaveText(en["verify.stamp_day"]);
});
