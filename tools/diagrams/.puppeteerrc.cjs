// Puppeteer is here only because the Mermaid CLI drives a browser through it. It must not fetch a
// browser of its own on install: render.mjs hands it the Chromium that Playwright already
// installs for apps/web, so npm ci needs no download beyond the packages in the lockfile.
module.exports = { skipDownload: true };
