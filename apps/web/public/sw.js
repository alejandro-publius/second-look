/* Second Look service worker. Hand written, no packages.
 * - Precaches the lesson and test screens plus the placeholder photos listed in /precache.json.
 * - Same-origin pages: network first, cache fallback, then /offline. A page is cached under its
 *   path and src only, never the rest of its query (see pageKey).
 * - Same-origin static files: cache first, refreshed in the background.
 * - Never touches the API origin, /api/ or anything cross-origin. Never caches POST.
 * - On a "sync" event or a "flush" message it asks open pages to send the offline queue
 *   (the queue lives in IndexedDB and the page code owns the send logic).
 */
// The cache name carries the content hash, so new photos and new copy replace the placeholders
// on the next visit instead of hiding behind a stale cache. build-content.mjs rewrites this line.
const VERSION = "sl-ca2a27ba9d712446";
const PRECACHE = `${VERSION}-precache`;
const RUNTIME = `${VERSION}-runtime`;

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(PRECACHE);
      let list = { pages: ["/", "/offline"], photos: [] };
      try {
        const res = await fetch("/precache.json", { cache: "no-store" });
        if (res.ok) list = await res.json();
      } catch {
        // offline at install: keep the minimal list
      }
      const urls = [...(list.pages || []), ...(list.photos || [])];
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
      await Promise.all(names.filter((n) => !n.startsWith(VERSION)).map((n) => caches.delete(n)));
      await self.clients.claim();
    })(),
  );
});

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
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/photos/") || url.pathname.startsWith("/icons/")) {
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
