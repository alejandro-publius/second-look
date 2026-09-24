// What the gallery script may send to the live site: reading only. Nothing it does there may start
// a study session, answer judge mode, send a creek check or upload a photo, so every request that
// could write is refused before it leaves the browser, and a refused request fails the run.
// scripts/tests/test_gallery.py runs these rules through node, so a change here is tested.

/**
 * Paths on the live site the gallery never asks for, whatever the method. /api/skeleton is here
 * because the Worker writes a row to the production database on every request to it, a GET too.
 */
export const NEVER_ON_LIVE = ["/api/test/", "/api/demo/", "/api/check/", "/api/quick/", "/api/upload", "/api/photo/", "/api/skeleton"];

/** True when the gallery may send this request to the live site. */
export function liveRequestAllowed(method, url, liveOrigin) {
  if (url.startsWith("data:") || url.startsWith("blob:")) return true;
  let target;
  try {
    target = new URL(url);
  } catch {
    return false;
  }
  if (target.origin !== new URL(liveOrigin).origin) return false;
  if (method !== "GET" && method !== "HEAD") return false;
  return !NEVER_ON_LIVE.some((p) => target.pathname.startsWith(p));
}

/** True when a request from the local build stays on this machine: the build or the mocked API. */
export function localRequestAllowed(url, allowedOrigins) {
  if (url.startsWith("data:") || url.startsWith("blob:")) return true;
  let target;
  try {
    target = new URL(url);
  } catch {
    return false;
  }
  return allowedOrigins.some((o) => new URL(o).origin === target.origin);
}
