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

test.describe("with service workers allowed", () => {
  test.use({ serviceWorkers: "allow" });

  test("the service worker installs and precaches the lesson screens and photos", async ({ page, context }) => {
    await page.goto("/");
    const worker = await context.waitForEvent("serviceworker", { timeout: 30_000 });
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
      .toEqual(expect.arrayContaining(["/t", "/check", "/photos/ph-warmup-01.jpg"]));
  });
});
