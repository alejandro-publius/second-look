import { expect, test } from "@playwright/test";

test("manifest and service worker are served from our origin", async ({ request }) => {
  const manifest = await request.get("/manifest.webmanifest");
  expect(manifest.status()).toBe(200);
  const m = await manifest.json();
  expect(m.name).toBe("Second Look");
  expect(m.display).toBe("standalone");
  expect(m.icons.length).toBeGreaterThanOrEqual(2);
  for (const icon of m.icons) expect((await request.get(icon.src)).status()).toBe(200);
  const sw = await request.get("/sw.js");
  expect(sw.status()).toBe(200);
  expect(await sw.text()).toContain("precache.json");
  const pre = await request.get("/precache.json");
  const list = await pre.json();
  expect(list.pages).toContain("/t");
  expect(list.photos.length).toBeGreaterThanOrEqual(38);
});

// CRITIC_11 W01: the install caches the files the precached pages load, and only those. This reads
// the pages as the server sends them, follows each stylesheet to its fonts and each script to the
// chunks it names, and compares that with the list, which scripts/precache-static.mjs writes.
test("precache.json lists exactly the /_next/static files the precached pages load", async ({ request }) => {
  const list = await (await request.get("/precache.json")).json();
  const named = new Set<string>();
  for (const path of list.pages as string[]) {
    const res = await request.get(path);
    if (!(res.headers()["content-type"] ?? "").includes("text/html")) continue;
    for (const m of (await res.text()).matchAll(/\/_next\/static\/[^"'\s)\\<>]+/g)) named.add(m[0]);
  }
  expect(named.size).toBeGreaterThan(0);
  const queue = [...named];
  while (queue.length) {
    const url = queue.pop()!;
    const res = await request.get(url);
    expect(res.status(), url).toBe(200);
    const text = url.endsWith(".css") || url.endsWith(".js") ? await res.text() : "";
    const refs = url.endsWith(".css")
      ? [...text.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/g)].map((m) => new URL(m[1], `http://x${url}`).pathname)
      : [...text.matchAll(/(?:\/_next\/)?static\/(?:chunks|media)\/[\w.~-]+/g)].map((m) => (m[0].startsWith("/") ? m[0] : `/_next/${m[0]}`));
    for (const ref of refs.filter((r) => r.startsWith("/_next/static/") && !named.has(r))) {
      named.add(ref);
      queue.push(ref);
    }
  }
  expect([...list.static].sort()).toEqual([...named].sort());
  // The scripts, the stylesheet and the font the page is set in are all there.
  expect(list.static.some((u: string) => u.endsWith(".js"))).toBe(true);
  expect(list.static.some((u: string) => u.endsWith(".css"))).toBe(true);
  expect(list.static.some((u: string) => u.endsWith(".woff2"))).toBe(true);
});

test.describe("with service workers allowed", () => {
  test.use({ serviceWorkers: "allow" });

  test("the service worker installs and precaches the lesson screens and photos", async ({ page, context }) => {
    const swEvent = context.waitForEvent("serviceworker", { timeout: 30_000 });
    await page.goto("/");
    const worker = await swEvent;
    expect(worker.url()).toBe("http://127.0.0.1:3100/sw.js");
    await page.evaluate(() => navigator.serviceWorker.ready);
    await expect
      .poll(
        async () =>
          page.evaluate(async () => {
            const names = await caches.keys();
            const pre = names.find((n) => n.endsWith("-precache"));
            if (!pre) return [];
            const cache = await caches.open(pre);
            return (await cache.keys()).map((r) => new URL(r.url).pathname);
          }),
        { timeout: 30_000 },
      )
      .toEqual(expect.arrayContaining(["/t", "/check", "/photos/offline/ph-warmup-03-640.avif"]));
  });

  // UPDATE_30 section 1 item 1: the worker before it kept every full-size photo, about 24 MB, in
  // its precache. A phone that still has them loses them when the new worker takes over, and a
  // cache left by an older version of the site goes too.
  test("a new worker drops what its list no longer names, and older caches", async ({ page }) => {
    const ready = () => page.waitForFunction(async () => (await navigator.serviceWorker.ready).active?.state === "activated", null, { timeout: 30_000 });
    const precache = () =>
      page.evaluate(async () => {
        const names = await caches.keys();
        const cache = await caches.open(names.find((n) => n.endsWith("-precache"))!);
        return { names, paths: (await cache.keys()).map((r) => new URL(r.url).pathname) };
      });
    await page.goto("/");
    await ready();
    const fresh = await precache();
    // As a phone that ran the old worker: a full-size photo in this precache, and an old cache.
    await page.evaluate(async () => {
      const name = (await caches.keys()).find((n) => n.endsWith("-precache"))!;
      await (await caches.open(name)).put("/photos/ph-bank-01.jpg", new Response("old photo", { headers: { "content-type": "image/jpeg" } }));
      await (await caches.open("sl-0000000000000000-precache")).put("/t", new Response("old page"));
      await (await navigator.serviceWorker.getRegistration())!.unregister();
    });
    expect((await precache()).paths).toContain("/photos/ph-bank-01.jpg");
    await page.reload();
    await ready();
    const after = await precache();
    const version = fresh.names.find((n) => n.endsWith("-precache"))!.replace(/-precache$/, "");
    expect(after.names.filter((n) => !n.startsWith(`${version}-`))).toEqual([]);
    expect(after.paths.sort()).toEqual(fresh.paths.sort());
  });

  // CRITIC_11 W01: the worker cached the pages at install but not the JavaScript, CSS and fonts
  // they load, and the first page's own files had loaded before the worker took control. Offline,
  // /check came back as bare HTML and Start the check did nothing, until a second visit online.
  // One visit of / is all a phone gets here, then the network goes.
  test("after one visit to /, the creek check opens and reaches its first question offline", async ({ page, context }) => {
    await page.goto("/");
    // ready resolves once the worker has installed, which is when its precache is filled.
    await page.waitForFunction(async () => (await navigator.serviceWorker.ready).active?.state === "activated", null, {
      timeout: 30_000,
    });
    await context.setOffline(true);
    await page.goto("/check");
    await expect(page.getByRole("heading", { name: "Creek check" })).toBeVisible();
    await page.getByRole("button", { name: "Start the check" }).click();
    await expect(page.getByRole("heading", { name: "Where are you?" })).toBeVisible();
    // Location is not granted here, so the pin, as on a phone where the person said no.
    await page.getByRole("button", { name: "Drop a pin instead" }).click();
    await page.getByLabel("Latitude").fill("37.8719");
    await page.getByLabel("Longitude").fill("-122.2585");
    await page.getByLabel("Name for this spot").fill("Footbridge");
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("Question 1 of")).toBeVisible();
    await context.setOffline(false);
  });
});
