// make design-check. Fails on anything docs/internal/updates/UPDATE_06.md section 6 bans, inside apps/web
// and content/. Static rules run always; the tap target measurement runs Playwright against the
// built app on the phone viewport, over the stage 1 screens only. SKIP_TAP=1 skips that part.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const web = resolve(here, "..");
const repo = resolve(web, "..", "..");
const TOKENS = join(web, "styles", "tokens.css");
const THEME = join(web, "app", "theme.ts");
const ICON = join(web, "components", "ui", "Icon.tsx");

const fails = [];
const SKIP_DIRS = new Set(["node_modules", ".next", "out", "test-results", "playwright-report", "generated", "screens", "public"]);

function walk(root, exts) {
  const out = [];
  if (!existsSync(root)) return out;
  for (const name of readdirSync(root)) {
    if (SKIP_DIRS.has(name)) continue;
    const p = join(root, name);
    if (statSync(p).isDirectory()) out.push(...walk(p, exts));
    else if (exts.some((e) => name.endsWith(e))) out.push(p);
  }
  return out;
}

function rel(p) {
  return relative(repo, p);
}

function fail(file, line, msg) {
  fails.push(`${rel(file)}:${line} ${msg}`);
}

function lines(file) {
  return readFileSync(file, "utf8").split("\n");
}

const code = [...walk(join(web, "app"), [".tsx", ".ts", ".css"]), ...walk(join(web, "components"), [".tsx", ".ts"]), ...walk(join(web, "lib"), [".ts"]), ...walk(join(web, "styles"), [".css"])];
const cssFiles = code.filter((f) => f.endsWith(".css"));
const tsxFiles = code.filter((f) => f.endsWith(".tsx"));
const contentFiles = [...walk(join(repo, "content"), [".yaml", ".json"])];

// 1. Dashes, emoji, middle dot as a separator, an arrow in a label.
const EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{1F000}-\u{1F2FF}]/u;
const ARROW = /[\u2190-\u21FF\u27F0-\u27FF\u2B00-\u2BFF]|->(?=["'\s<])/;
for (const f of [...code, ...contentFiles]) {
  lines(f).forEach((l, i) => {
    if (l.includes("\u2014")) fail(f, i + 1, "em dash");
    if (l.includes("\u2013")) fail(f, i + 1, "en dash");
    if (EMOJI.test(l)) fail(f, i + 1, "emoji");
    if (/\s\u00B7\s/.test(l)) fail(f, i + 1, "middle dot used as a separator");
    if (ARROW.test(l) && !/aria-|eslint|\/\//.test(l)) fail(f, i + 1, "arrow in a label");
  });
}

// 2. Uppercase with wide letter spacing: the small label above a heading.
for (const f of cssFiles) {
  const text = readFileSync(f, "utf8");
  for (const m of text.matchAll(/\{[^}]*\}/g)) {
    if (/text-transform:\s*uppercase/.test(m[0]) && /letter-spacing/.test(m[0])) {
      fail(f, text.slice(0, m.index).split("\n").length, "uppercase with letter spacing");
    }
  }
}

// 3. One icon family, no icon runtime, no hand drawn SVG.
const pkg = JSON.parse(readFileSync(join(web, "package.json"), "utf8"));
const deps = { ...pkg.dependencies, ...pkg.devDependencies };
for (const bad of ["lucide-react", "react-icons", "@heroicons/react", "feather-icons", "@tabler/icons-react", "react-feather"]) {
  if (deps[bad]) fails.push(`apps/web/package.json:1 second icon family ${bad}`);
}
for (const f of tsxFiles) {
  if (f === ICON) continue;
  lines(f).forEach((l, i) => {
    if (/<svg/.test(l) && !/photoframe-marks/.test(l)) fail(f, i + 1, "inline hand drawn SVG icon, use components/ui/Icon.tsx");
  });
}

// 4. Fonts: ours only, from our own origin.
for (const f of [...code, join(web, "package.json")]) {
  lines(f).forEach((l, i) => {
    if (/\bInter\b/.test(l) && !/Internal|interface|interact/i.test(l)) fail(f, i + 1, "Inter");
    if (/fonts\.googleapis|fonts\.gstatic|next\/font\/google/.test(l)) fail(f, i + 1, "font from another origin");
    if (/@font-face/.test(readFileSync(f, "utf8")) && /src:[^;]*https?:/.test(readFileSync(f, "utf8"))) fail(f, i + 1, "remote font src");
  });
}

// 5. Raw colour, gradient, glow, raw size outside tokens.css. Every source kind, not just CSS.
const tsFiles = code.filter((f) => f.endsWith(".ts"));
for (const f of [...cssFiles, ...tsxFiles, ...tsFiles]) {
  if (f === TOKENS || f === THEME) continue;
  lines(f).forEach((l, i) => {
    if (/#[0-9a-fA-F]{3}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{8}\b/.test(l)) fail(f, i + 1, "raw hex colour outside tokens.css");
    if (/\b(rgb|rgba|hsl|hsla)\(/.test(l)) fail(f, i + 1, "raw colour function outside tokens.css");
    if (/(linear|radial|conic)-gradient/.test(l)) fail(f, i + 1, "gradient");
    if (/border-radius:\s*[^;]*\d+(px|rem|em)/.test(l)) fail(f, i + 1, "raw radius, use var(--radius)");
    if (/\b(font-size|stroke-width|outline-width|border-width|letter-spacing|text-decoration-thickness)\s*:\s*[^;]*\b\d/.test(l)) fail(f, i + 1, "raw size, use a token");
    if (/text-shadow|drop-shadow|filter:\s*blur/.test(l)) fail(f, i + 1, "glow");
    if (/box-shadow:/.test(l) && !/inset/.test(l) && !/var\(--shadow/.test(l)) fail(f, i + 1, "glow or untokenised shadow");
  });
}

// 6. The meta theme colour mirrors --bg. A meta tag cannot read a variable, so this keeps it true.
{
  const tok = readFileSync(TOKENS, "utf8");
  const theme = readFileSync(THEME, "utf8");
  const light = tok.match(/--bg:\s*(#[0-9a-fA-F]{6});/);
  const dark = tok.slice(tok.indexOf("prefers-color-scheme: dark")).match(/--bg:\s*(#[0-9a-fA-F]{6});/);
  const lightBlock = tok.slice(0, tok.indexOf("prefers-color-scheme: dark"));
  const one = (name) => lightBlock.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6});`))?.[1];
  const mirrors = [
    ["THEME_LIGHT", light?.[1]],
    ["THEME_DARK", dark?.[1]],
    ["PRINT_INK", one("--print-ink")],
    ["PRINT_PAPER", one("--print-paper")],
    ["CARD_SURFACE", one("--surface")],
    ["CARD_INK", one("--ink")],
    ["CARD_INK_SOFT", one("--ink-soft")],
    ["CARD_FLAG", one("--flag")],
    ["CARD_LINE", one("--line-strong")],
  ];
  for (const [name, want] of mirrors) {
    const got = theme.match(new RegExp(`${name} = "(#[0-9a-fA-F]{6})"`))?.[1];
    if (!want || got?.toLowerCase() !== want.toLowerCase()) fails.push(`apps/web/app/theme.ts:1 ${name} is ${got} but tokens.css says ${want}`);
  }
}

// 7. Contrast, computed from the tokens themselves.
function srgb(hex) {
  const n = hex.replace("#", "");
  return [0, 2, 4].map((i) => {
    const c = parseInt(n.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
}
function lum(hex) {
  const [r, g, b] = srgb(hex);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function ratio(a, b) {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}
function tokenSet(text) {
  const out = {};
  for (const m of text.matchAll(/(--[a-z-]+):\s*(#[0-9a-fA-F]{6});/g)) out[m[1]] = m[2];
  return out;
}
{
  const text = readFileSync(TOKENS, "utf8");
  const cut = text.indexOf("prefers-color-scheme: dark");
  const light = tokenSet(text.slice(0, cut));
  const dark = { ...light, ...tokenSet(text.slice(cut)) };
  const PAIRS = [
    ["--ink", "--bg", 4.5],
    ["--ink", "--surface", 4.5],
    ["--ink-soft", "--surface", 4.5],
    ["--ink-soft", "--bg", 4.5],
    ["--on-flag", "--flag", 4.5],
    ["--ok", "--ok-bg", 4.5],
    ["--warn", "--warn-bg", 4.5],
    ["--bad", "--bad-bg", 4.5],
    ["--line-strong", "--surface", 3],
    ["--line-strong", "--bg", 3],
    // A filled gauge block against an empty one. The gauge is the one graphic that carries meaning.
    ["--flag", "--surface", 3],
  ];
  for (const [scheme, set] of [["light", light], ["dark", dark]]) {
    for (const [fg, bg, min] of PAIRS) {
      if (!set[fg] || !set[bg]) {
        fails.push(`apps/web/styles/tokens.css:1 ${scheme} is missing ${fg} or ${bg}`);
        continue;
      }
      const r = ratio(set[fg], set[bg]);
      if (r < min) fails.push(`apps/web/styles/tokens.css:1 ${scheme} ${fg} on ${bg} is ${r.toFixed(2)} to 1, under ${min}`);
    }
  }
  // White on the orange is banned outright.
  if (ratio("#ffffff", light["--flag"]) >= 4.5) fails.push("apps/web/styles/tokens.css:1 white would pass on the flag colour, which the brief bans");
}

// 8. Every input has a label, and no placeholder stands in for one.
for (const f of tsxFiles) {
  const ls = lines(f);
  ls.forEach((l, i) => {
    if (!/<input\b/.test(l)) return;
    // The tag can span several lines, so take it whole, plus a little context for a wrapping label.
    let tag = "";
    for (let j = i; j < Math.min(ls.length, i + 20); j++) {
      tag += ls[j] + " ";
      if (/\/>|>\s*$/.test(ls[j]) && j > i) break;
      if (/\/>/.test(ls[j])) break;
    }
    const before = ls.slice(Math.max(0, i - 4), i).join(" ");
    const labelled = /aria-label|aria-labelledby|\bid=/.test(tag) || /<label/.test(before);
    if (!labelled) fail(f, i + 1, "input without a label");
    if (/placeholder=/.test(tag) && !/<label/.test(before) && !/aria-label/.test(tag)) fail(f, i + 1, "placeholder used as a label");
  });
}

// 9. Three equal cards in a row, a carousel, a custom cursor, a scroll cue, a version label.
for (const f of cssFiles) {
  lines(f).forEach((l, i) => {
    if (/grid-template-columns:\s*(repeat\(3|1fr 1fr 1fr)/.test(l)) fail(f, i + 1, "three equal cards in a row");
    if (/scroll-snap-type:\s*x|carousel/i.test(l)) fail(f, i + 1, "carousel");
    if (/cursor:\s*(url\(|none)/.test(l)) fail(f, i + 1, "custom cursor");
  });
}
for (const f of [...tsxFiles, ...contentFiles]) {
  lines(f).forEach((l, i) => {
    if (/scroll (down|for more)|scroll-cue/i.test(l)) fail(f, i + 1, "scroll cue");
    if (/["'>]\s*v\d+\.\d+/.test(l) && !/consent_version|form|schema/i.test(l)) fail(f, i + 1, "version label on a screen");
  });
}

// 10. The screenshots in docs/screens are real captures, not boxes drawn to look like screens.
{
  const dir = join(repo, "docs", "screens");
  if (existsSync(dir)) {
    for (const name of readdirSync(dir).filter((n) => n.endsWith(".png"))) {
      const size = statSync(join(dir, name)).size;
      if (size < 8000) fails.push(`docs/screens/${name}:1 too small to be a real screenshot (${size} bytes)`);
    }
  }
}

// 11. Tap targets on the phone viewport, stage 1 screens only.
let tapNote = "skipped (SKIP_TAP=1)";
if (process.env.SKIP_TAP !== "1") {
  const started = spawn("npm", ["run", "start"], { cwd: web, stdio: "ignore", detached: true, env: { ...process.env, NEXT_PUBLIC_API_ORIGIN: "http://127.0.0.1:8100", NEXT_PUBLIC_SITE_URL: "http://127.0.0.1:3100", NEXT_PUBLIC_BUILD_HASH: "test", NEXT_TELEMETRY_DISABLED: "1" } });
  const deadline = Date.now() + 60_000;
  let up = false;
  while (Date.now() < deadline && !up) {
    const probe = spawnSync("curl", ["-sS", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:3100/"], { encoding: "utf8" });
    up = probe.stdout === "200";
    if (!up) spawnSync("sleep", ["1"]);
  }
  if (!up) {
    fails.push("apps/web:1 could not start the app to measure tap targets");
  } else {
    const run = spawnSync("npx", ["playwright", "test", "tests/design.spec.ts", "--reporter=line"], { cwd: web, encoding: "utf8", env: { ...process.env, PW_REUSE: "1" } });
    const out = `${run.stdout}${run.stderr}`;
    if (run.status !== 0 && /Executable doesn't exist|playwright install/.test(out)) {
      // A missing browser is a setup step, not a failed measurement: say which one.
      fails.push("apps/web:1 Playwright's Chromium is not installed: run (cd apps/web && npx playwright install chromium)");
    } else if (run.status !== 0) {
      fails.push("apps/web/tests/design.spec.ts:1 tap target measurement failed");
      console.log(out.split("\n").filter((l) => l.trim()).slice(-25).join("\n"));
      tapNote = "FAILED";
    } else {
      tapNote = (out.match(/^\s*\d+ passed.*$/m) || ["passed"])[0].trim();
    }
  }
  try {
    process.kill(-started.pid);
  } catch {
    // already gone
  }
}

if (fails.length) {
  console.error("design-check FAILED");
  for (const f of fails) console.error(`  ${f}`);
  process.exit(1);
}
console.log(`design-check: clean. ${code.length} source files and ${contentFiles.length} content files scanned, contrast computed from tokens.css, tap targets ${tapNote}.`);
