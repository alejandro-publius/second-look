"use client";

import { useSyncExternalStore } from "react";

/**
 * Reads one query parameter. Cloudflare Pages serves a static export, so a page cannot read
 * search params on the server: /spot/<id> became /spot?id=<id>. useSyncExternalStore rather than
 * useSearchParams, because that one forces a Suspense boundary and a client bail out.
 * The server snapshot is empty, so the first paint matches on both sides.
 */
export function useQueryParam(name: string): string {
  return useSyncExternalStore(
    () => () => undefined,
    () => new URLSearchParams(window.location.search).get(name) ?? "",
    () => "",
  );
}

/**
 * The same, but null until the browser has read the address, so a page can tell a link with no
 * value ("") from one not read yet, and never asks the API about an empty id (REVIEW_03 R43).
 */
export function useQueryParamOrNull(name: string): string | null {
  return useSyncExternalStore(
    () => () => undefined,
    () => new URLSearchParams(window.location.search).get(name) ?? "",
    () => null,
  );
}
