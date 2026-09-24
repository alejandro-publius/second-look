// Prints the report's HTML to PDF in the Chromium that Playwright installs for apps/web
// (`npx playwright install chromium`), so nothing is downloaded and no network is needed.
//
//   node scripts/print-report.mjs <report.html> <out.pdf>
//
// scripts/build_report.py runs this for `make report-pdf`; it is not meant to be run by hand.
// It prints one line of JSON on success: the browser's version, for the stamp in
// results/report_pdf.json. The page opens from a file, and any request to the network is
// refused, so a report that tried to load something from elsewhere fails here.

import { chromium } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [htmlArg, pdfArg] = process.argv.slice(2);
if (!htmlArg || !pdfArg) {
  console.error("print-report: node scripts/print-report.mjs <report.html> <out.pdf>");
  process.exit(2);
}
const html = path.resolve(htmlArg);
if (!existsSync(html)) {
  console.error(`print-report: no such file: ${html}`);
  process.exit(2);
}

const FOOTER =
  '<div style="width:100%;font-size:7pt;color:#4d5a56;text-align:center;font-family:Helvetica,Arial,sans-serif">' +
  'Second Look, technical report. Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>';

const browser = await chromium.launch();
const blocked = [];
try {
  const page = await browser.newPage();
  await page.route("**/*", (route) => {
    const url = route.request().url();
    if (url.startsWith("file:") || url.startsWith("data:")) return route.continue();
    blocked.push(url);
    return route.abort();
  });
  await page.goto(pathToFileURL(html).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  if (blocked.length > 0) {
    console.error(`print-report: the report asked the network for ${blocked.length} thing(s): ${blocked.join(", ")}`);
    process.exitCode = 1;
  } else {
    await page.pdf({
      path: path.resolve(pdfArg),
      format: "A4",
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: "<span></span>",
      footerTemplate: FOOTER,
      margin: { top: "15mm", bottom: "16mm", left: "16mm", right: "16mm" },
      // Tagged, so a screen reader can read the headings, lists and tables in order, and with an
      // outline of the headings, so a reader can jump between sections (hard rule 17).
      tagged: true,
      outline: true,
    });
    console.log(JSON.stringify({ browser: `Chromium ${browser.version()}` }));
  }
} finally {
  await browser.close();
}
