// What a first visit may download in the background, and what it downloads (UPDATE_30 section 1
// item 1). The service worker used to precache every photo the site shows, about 24 MB, on any
// first visit. Now it keeps only what the two-minute test and the creek check need offline: the
// pages below with their scripts, styles and fonts, and one phone-size copy of each photo of the
// test. Everything else is fetched when it is opened, and cached after that.
//
// scripts/build-content.mjs writes the pages and the photos into public/precache.json,
// scripts/precache-static.mjs adds the /_next/static files and fails the build over the budget,
// and tests/offline-budget.spec.ts measures a real first visit against it.

/** 3 MB, counted as 3,000,000 bytes of response bodies, the stricter of the two ways to count. */
export const BACKGROUND_BUDGET_BYTES = 3_000_000;

/**
 * The pages kept for offline use: the landing page, the test, the creek check (the site promises
 * it works offline once the site has been opened) and the page shown for any other page offline.
 */
export const OFFLINE_PAGES = ["/", "/t", "/check", "/offline", "/manifest.webmanifest"];
