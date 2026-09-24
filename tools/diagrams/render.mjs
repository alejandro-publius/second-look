// Draws every docs/diagrams/<name>.mmd as docs/diagrams/<name>.svg (UPDATE_27 block 23).
//
//   node render.mjs            render each diagram and write its SVG when the bytes changed
//   node render.mjs --check    render each one again in memory and fail when a render fails,
//                              when an SVG is missing or has no source, when an SVG's stamp names
//                              another source, config or renderer, or when the SVG differs in
//                              content from the fresh render
//   node render.mjs --png DIR  also write a PNG of each diagram to DIR, to look at while editing
//
// The renderer is pinned in package.json and package-lock.json next to this file: the Mermaid CLI
// and the Mermaid it loads. The browser is the Chromium that Playwright installs for apps/web
// (`npx playwright install chromium`), found through playwright-core at the same version as
// apps/web's, so nothing is downloaded here and the render needs no network.
//
// Bytes or content? A render is byte for byte the same on one machine, run after run. Across
// machines it is not: Mermaid measures every label in the browser, and a Mac and a Linux runner
// measure text with different fonts, so boxes and lines land a pixel or two apart. So the check
// takes three steps. First, the stamp at the top of each SVG must carry the sha256 of the .mmd
// source and of the config, and the renderer's versions, as they are now: an edited source that
// was not rendered again fails here, whatever machine runs the check. Second, the stamp carries
// the sha256 of the drawing under it, so a hand edit to the SVG fails, even one that only moves
// a box. Third, a fresh render must equal the committed SVG byte for byte, or, when it does not,
// equal it once every number inside a tag is set aside (positions, sizes, path data): every
// label, node, edge, class, colour and the order of them all must still match.

import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { renderMermaid } from "@mermaid-js/mermaid-cli";
import { chromium } from "playwright-core";
import puppeteer from "puppeteer";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const DIAGRAMS = process.env.DIAGRAMS_DIR ? path.resolve(process.env.DIAGRAMS_DIR) : path.join(ROOT, "docs", "diagrams");
const CONFIG = path.join(HERE, "mermaid.config.json");
const STAMP_RE = /^<!-- Drawn by make diagrams [^\n]*? -->\n/;

function sha256(text) {
  return createHash("sha256").update(text).digest("hex");
}

function versionOf(pkg) {
  const file = path.join(HERE, "node_modules", ...pkg.split("/"), "package.json");
  return JSON.parse(readFileSync(file, "utf8")).version;
}

/** What an SVG was drawn from and with: the start of its first line. */
export function stampHead(name, source, configText, versions) {
  return (
    `<!-- Drawn by make diagrams from docs/diagrams/${name}.mmd (sha256 ${sha256(source)}) ` +
    `with tools/diagrams/mermaid.config.json (sha256 ${sha256(configText)}), ` +
    `@mermaid-js/mermaid-cli ${versions.cli} and mermaid ${versions.mermaid}; `
  );
}

/** The first line of every SVG: the head, then the sha256 of the drawing that follows it. */
export function stampFor(name, source, configText, versions, body) {
  return `${stampHead(name, source, configText, versions)}the drawing below has sha256 ${sha256(body)}. Edit the .mmd file, never this one. -->\n`;
}

const DRAWING_RE = /the drawing below has sha256 ([0-9a-f]{64})\. /;

/** Split a committed SVG into its stamp and its drawing. */
export function splitStamp(svg) {
  const stamp = (svg.match(STAMP_RE) ?? [""])[0];
  return { stamp, body: svg.slice(stamp.length), drawingSha: (stamp.match(DRAWING_RE) ?? [])[1] ?? null };
}

export { sha256 };

/** The SVG with its stamp and every number inside a tag set aside, for the content comparison.
 *  data-points holds an edge's coordinates in base64, so it is set aside whole. Text between
 *  tags, the labels and the style sheet, is kept exactly. */
export function signature(svg) {
  return svg
    .replace(STAMP_RE, "")
    .replace(/<[^>]*>/g, (tag) => tag.replace(/\sdata-points="[^"]*"/g, "").replace(/[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?/gi, "#"));
}

/** Where two texts first part, with a little context, for the failure message. */
function firstDifference(a, b) {
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i += 1;
  const from = Math.max(0, i - 60);
  return { committed: a.slice(from, i + 60), fresh: b.slice(from, i + 60) };
}

function diagramNames() {
  if (!existsSync(DIAGRAMS)) return { sources: [], orphans: [] };
  const files = readdirSync(DIAGRAMS);
  const sources = files.filter((f) => f.endsWith(".mmd")).map((f) => f.slice(0, -4)).sort();
  const orphans = files.filter((f) => f.endsWith(".svg") && !sources.includes(f.slice(0, -4))).sort();
  return { sources, orphans };
}

async function launch() {
  const executablePath = process.env.DIAGRAMS_CHROMIUM || chromium.executablePath();
  if (!existsSync(executablePath)) {
    throw new Error(`no Chromium at ${executablePath}; run: cd apps/web && npx playwright install chromium`);
  }
  // --no-sandbox as Playwright itself launches Chromium: the pages are our own local files, and a
  // CI runner's kernel may refuse the sandbox. Hinting off so text is measured the same way on
  // every platform that has the font.
  return puppeteer.launch({ executablePath, headless: true, args: ["--no-sandbox", "--font-render-hinting=none"] });
}

async function draw(browser, name, source, mermaidConfig, format = "svg") {
  const { data } = await renderMermaid(browser, source, format, {
    mermaidConfig,
    backgroundColor: "white",
    svgId: `sl-${name}`,
    viewport: { width: 1200, height: 800, deviceScaleFactor: format === "png" ? 2 : 1 },
  });
  return format === "svg" ? new TextDecoder().decode(data) : data;
}

async function main(argv) {
  const check = argv.includes("--check");
  const pngAt = argv.indexOf("--png");
  const pngDir = pngAt >= 0 ? path.resolve(argv[pngAt + 1] ?? ".") : null;
  const configText = readFileSync(CONFIG, "utf8");
  const mermaidConfig = JSON.parse(configText);
  const versions = { cli: versionOf("@mermaid-js/mermaid-cli"), mermaid: versionOf("mermaid") };
  const { sources, orphans } = diagramNames();
  const problems = orphans.map((f) => `${f}: an SVG with no .mmd source next to it`);
  if (sources.length === 0) problems.push(`no .mmd sources in ${path.relative(ROOT, DIAGRAMS) || DIAGRAMS}`);
  const lines = [];
  let browser;
  try {
    browser = await launch();
    for (const name of sources) {
      const source = readFileSync(path.join(DIAGRAMS, `${name}.mmd`), "utf8");
      const svgPath = path.join(DIAGRAMS, `${name}.svg`);
      const head = stampHead(name, source, configText, versions);
      let fresh;
      try {
        const body = (await draw(browser, name, source, mermaidConfig)) + "\n";
        fresh = stampFor(name, source, configText, versions, body) + body;
      } catch (err) {
        problems.push(`${name}.mmd: does not render: ${String(err?.message ?? err).split("\n").slice(0, 3).join(" ")}`);
        continue;
      }
      if (pngDir) {
        mkdirSync(pngDir, { recursive: true });
        writeFileSync(path.join(pngDir, `${name}.png`), await draw(browser, name, source, mermaidConfig, "png"));
      }
      const committed = existsSync(svgPath) ? readFileSync(svgPath, "utf8") : null;
      if (!check) {
        if (committed === fresh) lines.push(`${name}.svg: unchanged`);
        else {
          writeFileSync(svgPath, fresh);
          lines.push(`${name}.svg: written`);
        }
        continue;
      }
      if (committed === null) {
        problems.push(`${name}.svg: missing; run make diagrams-render`);
        continue;
      }
      const mine = splitStamp(committed);
      if (!mine.stamp.startsWith(head)) {
        problems.push(`${name}.svg: its stamp does not match ${name}.mmd, the config and the renderer as they are now; run make diagrams-render`);
        continue;
      }
      if (mine.drawingSha !== sha256(mine.body)) {
        problems.push(`${name}.svg: edited by hand after it was drawn: the drawing's sha256 is not the one in its stamp; run make diagrams-render`);
        continue;
      }
      if (committed === fresh) {
        lines.push(`${name}.svg: the same bytes as a fresh render`);
      } else if (signature(committed) === signature(fresh)) {
        lines.push(`${name}.svg: the same content as a fresh render; positions differ with this machine's fonts`);
      } else {
        const d = firstDifference(signature(committed), signature(fresh));
        problems.push(`${name}.svg: differs in content from a fresh render of ${name}.mmd; run make diagrams-render\n  committed: ${d.committed}\n  fresh:     ${d.fresh}`);
      }
    }
  } catch (err) {
    problems.push(String(err?.message ?? err));
  } finally {
    await browser?.close();
  }
  for (const line of lines) console.log(`diagrams: ${line}`);
  if (problems.length > 0) {
    for (const p of problems) console.log(`diagrams: ${p}`);
    console.log(`diagrams: ${problems.length} problem(s) in ${sources.length} diagram(s)`);
    return 1;
  }
  const how = check ? "match a fresh render" : "rendered";
  console.log(`diagrams: ${sources.length} diagram(s) ${how}, @mermaid-js/mermaid-cli ${versions.cli}, mermaid ${versions.mermaid}`);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main(process.argv.slice(2));
}
