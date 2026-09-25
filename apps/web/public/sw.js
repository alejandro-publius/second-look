/* Second Look service worker. Hand written, no packages.
 * - Precaches what /precache.json lists and nothing more: the pages the two-minute test and the
 *   creek check need offline, the /_next/static files they load (scripts/precache-static.mjs), and
 *   one phone-size copy of each photo of the test. The build keeps that under 3 MB
 *   (offline-budget.mjs). Every other page, photo and file is cached only once it is opened.
 * - Same-origin pages: network first, cache fallback, then /offline. A page is cached under its
 *   path and src only, never the rest of its query (see pageKey).
 * - Same-origin static files: cache first, refreshed in the background.
 * - Photos: the same, and when a photo of the test can neither be found in a cache nor fetched,
 *   its phone-size copy from the precache, as the list's fallbacks name it. Online a page always
 *   gets the photo it asked for.
 * - Never touches the API origin, /api/ or anything cross-origin. Never caches POST.
 * - On a "sync" event or a "flush" message it asks open pages to send the offline queue
 *   (the queue lives in IndexedDB and the page code owns the send logic).
 */
// The cache name carries the content hash, so new photos and new copy replace the placeholders
// on the next visit instead of hiding behind a stale cache. build-content.mjs rewrites this line.
const VERSION = "sl-6e5e077e15ff23bc";
const PRECACHE = `${VERSION}-precache`;
const RUNTIME = `${VERSION}-runtime`;
// The list is kept in the precache too, so the fetch handler can read its fallbacks offline.
const LIST = "/precache.json";

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(PRECACHE);
      let list = { pages: ["/", "/offline"], photos: [] };
      try {
        const res = await fetch(LIST, { cache: "no-store" });
        if (res.ok) {
          list = await res.clone().json();
          await cache.put(LIST, res);
        }
      } catch {
        // offline at install: keep the minimal list
      }
      const urls = [...(list.pages || []), ...(list.static || []), ...(list.photos || [])];
      await Promise.all(
        urls.map((u) =>
          cache.add(u).catch(() => {
            // one missing file must not fail the whole install
          }),
        ),
      );
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(names.filter((n) => n !== PRECACHE && n !== RUNTIME).map((n) => caches.delete(n)));
      await prunePrecache();
      await self.clients.claim();
    })(),
  );
});

/**
 * Drops from the precache what the current list no longer names: last build's scripts, and on a
 * phone that ran the worker before UPDATE_30, the full-size photos, about 24 MB, it kept there.
 */
async function prunePrecache() {
  const cache = await caches.open(PRECACHE);
  const list = await storedList();
  if (!list) return;
  const keep = new Set([LIST, ...(list.pages || []), ...(list.static || []), ...(list.photos || [])].map((u) => new URL(u, self.location.origin).href));
  const keys = await cache.keys();
  await Promise.all(keys.filter((req) => !keep.has(req.url)).map((req) => cache.delete(req)));
}

async function storedList() {
  const res = await (await caches.open(PRECACHE)).match(LIST);
  if (!res) return null;
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function isSameOrigin(url) {
  return url.origin === self.location.origin;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (!isSameOrigin(url)) return;
  if (url.pathname.startsWith("/api/")) return;
  // Walk clips stream straight from the network: a browser asks for them in byte ranges, and a
  // 20 MB clip has no business in a phone's cache.
  if (url.pathname.startsWith("/walks/")) return;

  if (req.mode === "navigate" || url.searchParams.has("_rsc")) {
    event.respondWith(networkFirst(req));
    return;
  }
  if (url.pathname.startsWith("/photos/")) {
    event.respondWith(photo(req));
    return;
  }
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(cacheFirst(req));
    return;
  }
  event.respondWith(networkFirst(req));
});

// The cache key of a page: its path, plus src when the link has one. A research panel adds its own
// identifiers to our link, and nothing but src from a link may be kept (docs/internal/PANEL_STUDY.md).
// Every page reads its query in the browser, so one copy per path and src serves any query.
function pageKey(req) {
  const url = new URL(req.url);
  const src = url.searchParams.get("src");
  return url.origin + url.pathname + (src === null ? "" : `?src=${encodeURIComponent(src)}`);
}

async function networkFirst(req) {
  const cache = await caches.open(RUNTIME);
  const key = req.mode === "navigate" ? pageKey(req) : req;
  try {
    const res = await fetch(req);
    if (res && res.ok) cache.put(key, res.clone()).catch(() => undefined);
    return res;
  } catch {
    const hit = (await cache.match(key)) || (await caches.match(key));
    if (hit) return hit;
    if (req.mode === "navigate") {
      const offline = await caches.match("/offline");
      if (offline) return offline;
    }
    return new Response("offline", { status: 503, headers: { "content-type": "text/plain" } });
  }
}

async function cacheFirst(req) {
  const hit = await caches.match(req);
  if (hit) {
    fetch(req)
      .then((res) => (res && res.ok ? caches.open(RUNTIME).then((c) => c.put(req, res)) : undefined))
      .catch(() => undefined);
    return hit;
  }
  const res = await fetch(req);
  if (res && res.ok) {
    const cache = await caches.open(RUNTIME);
    cache.put(req, res.clone()).catch(() => undefined);
  }
  return res;
}

// A photo from a cache or the network, as any static file. Only when both fail, which means the
// phone is offline and never opened this photo online, does a photo of the test come back as its
// phone-size copy: smaller, but the same whole picture, so the test goes on offline.
async function photo(req) {
  try {
    return await cacheFirst(req);
  } catch (err) {
    const list = await storedList();
    const copy = list && list.fallbacks ? list.fallbacks[new URL(req.url).pathname] : undefined;
    const hit = copy ? await caches.match(copy) : undefined;
    if (hit) return hit;
    throw err;
  }
}

async function askPagesToFlush() {
  const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  for (const c of clients) c.postMessage({ type: "sl-flush" });
}

self.addEventListener("sync", (event) => {
  if (event.tag === "sl-queue") event.waitUntil(askPagesToFlush());
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "sl-flush") askPagesToFlush();
});
