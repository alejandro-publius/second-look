import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { expect, test, type BrowserContext, type Locator, type Page } from "@playwright/test";
import { content, FEATURE_IDS, photoById } from "../lib/content";
import { BACKGROUND_BUDGET_BYTES } from "../offline-budget.mjs";
import { mockApi } from "./mock-api.mjs";
import { answerItem, passConsent, pickWarmup } from "./helpers";

/**
 * UPDATE_30 section 1 item 1, critic round 13 P01. One look at any page started a background
 * download of about 24 MB, every photo the site shows, and the test was ready offline only once it
 * finished. Now the service worker keeps only what the two-minute test and the creek check need
 * offline, and a first visit may download no more than 3 MB in the background.
 *
 *   PRECACHE_BUDGET_OUT=../../results/precache_budget.json npx playwright test tests/offline-budget.spec.ts
 *
 * writes the measured number to results/ (make precache-budget does exactly that).
 */
test.use({ serviceWorkers: "allow" });

interface Fetched {
  path: string;
  /** The body as Chromium could hand it over, which is empty once the worker has read it. */
  body: number;
  /** content-length, when the server sent one (it sends none for a compressed file). */
  length: number;
  /** Bytes on the wire, compressed, and 0 when the file came from the browser's HTTP cache. */
  wire: number;
}

/** Every response the service worker fetched itself, the worker's own script included. */
function watchWorker(context: BrowserContext) {
  const fetched: Fetched[] = [];
  const pending: Promise<void>[] = [];
  context.on("requestfinished", (req) => {
    if (!req.serviceWorker()) return;
    pending.push(
      (async () => {
        const res = await req.response();
        if (!res) return;
        const body = await res.body().catch(() => Buffer.alloc(0));
        const wire = Math.max(0, (await req.sizes()).responseBodySize);
        fetched.push({ path: new URL(req.url()).pathname, body: body.length, length: Number(res.headers()["content-length"] ?? 0), wire });
      })(),
    );
  });
  return { fetched, settled: () => Promise.all(pending) };
}

/** Every entry in Cache Storage, with the size of its body. */
function cacheStorage(page: Page) {
  return page.evaluate(async () => {
    const out: { cache: string; path: string; bytes: number }[] = [];
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      for (const req of await cache.keys()) {
        const res = await cache.match(req);
        out.push({ cache: name, path: new URL(req.url).pathname, bytes: res ? (await res.blob()).size : 0 });
      }
    }
    return out;
  });
}

const sum = (xs: { bytes: number }[]) => xs.reduce((n, x) => n + x.bytes, 0);

test("a first visit to / downloads no more than 3 MB in the background", async ({ page, context }) => {
  test.setTimeout(120_000);
  const worker = watchWorker(context);
  await page.goto("/");
  await page.waitForTimeout(30_000);
  await worker.settled();

  // The worker installed and filled its precache, so the sum below is of a real install and
  // not of a worker that never started.
  const list = await (await page.request.get("/precache.json")).json();
  const wanted: string[] = [...list.pages, ...list.static, ...list.photos, "/precache.json"];
  const stored = await cacheStorage(page);
  const precache = stored.filter((e) => e.cache.endsWith("-precache"));
  expect(precache.map((e) => e.path).sort()).toEqual([...new Set(wanted)].sort());
  // Every file it keeps passed through the count as the worker fetched it.
  const counted = new Set(worker.fetched.map((f) => f.path));
  expect(wanted.filter((p) => !counted.has(p))).toEqual([]);

  // Each response counts at its full size, uncompressed. Chromium gives the worker's bodies to the
  // worker, not to the test, so the size is the largest of what it did report: the body, the
  // content-length, the stored copy in Cache Storage and the bytes on the wire. The largest never
  // undercounts, and a file fetched twice counts twice.
  const storedSize = new Map<string, number>();
  for (const e of stored) storedSize.set(e.path, Math.max(storedSize.get(e.path) ?? 0, e.bytes));
  const sized = worker.fetched.map((f) => ({ path: f.path, bytes: Math.max(f.body, f.length, f.wire, storedSize.get(f.path) ?? 0) }));
  const bytes = sum(sized);
  const cacheBytes = sum(stored);
  const out = process.env.PRECACHE_BUDGET_OUT;
  if (out) {
    const git = (cmd: string) => execSync(cmd, { encoding: "utf8" }).trim();
    const photos = sized.filter((f) => f.path.startsWith("/photos/"));
    const result = {
      what: "Every response body the service worker fetched in the 30 seconds after a first visit to / on the phone profile, uncompressed, with nothing cached before",
      made_by: "apps/web/tests/offline-budget.spec.ts through make precache-budget",
      page: "/",
      profile: "Playwright iPhone 13 in Chromium, service workers allowed",
      waited_seconds: 30,
      budget_bytes: BACKGROUND_BUDGET_BYTES,
      bytes,
      megabytes: Math.round(bytes / 10_000) / 100,
      files: sized.length,
      photos: { files: photos.length, bytes: sum(photos) },
      wire_bytes: worker.fetched.reduce((n, f) => n + f.wire, 0),
      cache_storage_bytes: cacheBytes,
      under_budget: bytes <= BACKGROUND_BUDGET_BYTES,
      measured_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      commit: git("git rev-parse HEAD"),
      // Every build rewrites public/_headers with the API origin it was given, so that file aside.
      tree_clean: git("git status --porcelain -- . ../../photos ../../content ':(exclude)public/_headers'") === "",
    };
    const path = resolve(out);
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, JSON.stringify(result, null, 2) + "\n");
  }
  expect(bytes).toBeLessThanOrEqual(BACKGROUND_BUDGET_BYTES);
  expect(cacheBytes).toBeLessThanOrEqual(BACKGROUND_BUDGET_BYTES);

  // Of the photos, one phone-size copy of each photo the two-minute test shows, and no full-size one.
  const testFlowPhotos = new Set([
    ...content.warmup.map((w) => w.photo_id),
    ...Object.values(content.lessons).flatMap((l) => [...l.contrast_pairs.flatMap((p) => [p.assume_photo_id, p.actual_photo_id]), l.practice.photo_id]),
    ...content.test_items.map((i) => i.photo_id),
  ]);
  expect(list.photos).toHaveLength(testFlowPhotos.size);
  expect(precache.filter((e) => e.path.startsWith("/photos/") && !e.path.startsWith("/photos/offline/"))).toEqual([]);
});

/** Waits until this photo has loaded and drawn, and returns the address the page asked for. */
async function loaded(img: Locator): Promise<string> {
  await expect(img).toBeVisible();
  await expect.poll(() => img.evaluate((el) => (el as HTMLImageElement).complete && (el as HTMLImageElement).naturalWidth > 0)).toBe(true);
  return (await img.getAttribute("src")) ?? "";
}

const shown = (page: Page, id: string) => page.locator(`img.photo[src="${photoById(id)!.url}"]`);

test("after one visit, a sitting started online goes through the lesson and all 16 photos offline", async ({ page, context }) => {
  test.setTimeout(180_000);
  const offline = { value: false };
  const calls = await mockApi(page, { lessonFirst: true, offline });

  // One visit, then the worker is installed and its precache is full.
  await page.goto("/");
  await page.waitForFunction(async () => (await navigator.serviceWorker.ready).active?.state === "activated", null, { timeout: 30_000 });

  // A sitting needs the server once: it assigns the arm, as the tagged plan says.
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await expect(page.locator(".gauge-count", { hasText: "Built banks" })).toBeVisible();
  expect(calls.filter((c) => c.path === "/api/test/session")).toHaveLength(1);
  const first = content.lessons.artificial_bank.contrast_pairs[0];
  await loaded(shown(page, first.assume_photo_id));
  await loaded(shown(page, first.actual_photo_id));

  // Then the network goes, for the whole lesson and all 16 photos.
  const images: { path: string; fromWorker: boolean; status: number; type: string }[] = [];
  const failed: string[] = [];
  page.on("response", (r) => {
    if (r.request().resourceType() === "image") images.push({ path: new URL(r.url()).pathname, fromWorker: r.fromServiceWorker(), status: r.status(), type: r.headers()["content-type"] ?? "" });
  });
  page.on("requestfailed", (r) => {
    if (r.resourceType() === "image") failed.push(r.url());
  });
  offline.value = true;
  await context.setOffline(true);

  for (const feature of FEATURE_IDS) {
    const lesson = content.lessons[feature];
    if (feature !== "artificial_bank") {
      await loaded(shown(page, lesson.contrast_pairs[0].assume_photo_id));
      await loaded(shown(page, lesson.contrast_pairs[0].actual_photo_id));
    }
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await loaded(shown(page, lesson.contrast_pairs[1].assume_photo_id));
    await loaded(shown(page, lesson.contrast_pairs[1].actual_photo_id));
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await expect(page.getByText("Try one.")).toBeVisible();
    await loaded(shown(page, lesson.practice.photo_id));
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await expect(page.getByRole("status")).toBeVisible();
    await loaded(shown(page, lesson.practice.photo_id));
    await page.getByRole("button", { name: feature === "pipe_running" ? "Finish" : "Next photo", exact: true }).click();
  }

  const testPhotos = new Set<string>();
  for (let i = 1; i <= 16; i++) {
    await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
    testPhotos.add(await loaded(page.locator("img.photo-large")));
    // Every answer waits on the phone, and the page says so.
    if (i > 1) await expect(page.getByText("Some answers have not sent yet.")).toBeVisible();
    await answerItem(page, "Yes");
  }
  // All 16 photos of the test were shown, each one drawn.
  expect([...testPhotos].sort()).toEqual(content.test_items.map((item) => photoById(item.photo_id)!.url).sort());
  await expect(page.getByRole("heading", { name: "Almost done" })).toBeVisible();

  // Every photo came from the worker's cache, as its phone-size copy, and none failed.
  expect(failed).toEqual([]);
  expect(images.length).toBeGreaterThanOrEqual(16);
  expect(images.filter((i) => !i.fromWorker || i.status !== 200)).toEqual([]);
  expect(images.filter((i) => i.path.endsWith(".jpg") && i.type !== "image/avif")).toEqual([]);

  const whileOffline = calls.length;

  // The network comes back, and every answer arrives before the score is shown.
  offline.value = false;
  await context.setOffline(false);
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
  const after = calls.slice(whileOffline);
  const arrived = new Set(after.filter((c) => c.path === "/api/test/response").map((c) => c.body.item_id));
  expect(arrived.size).toBe(16);
  // The first complete found none of them and named all 16; the second came after they were sent.
  const completes = after.filter((c) => c.path === "/api/test/complete");
  expect(completes.map((c) => Boolean(c.body.final))).toEqual([false, true]);
  // All sixteen answered Yes: the mock's key has two present and two absent per feature.
  await expect(page.getByText("8 of 16 right")).toBeVisible();
});
