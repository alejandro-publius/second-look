// Build-time content step. Reads the YAML, the locale and the photo manifest from the repo root,
// writes generated/content.json for the app, copies only manifest-listed images into public/photos/,
// and writes public/precache.json for the service worker. Gold labels never reach the browser:
// `gold` is stripped from test items and `gold_label` from photos before anything is written.
// Runs as `prebuild` and `predev`. Node 20 or newer; nothing beyond Node 20 APIs.
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";
import { load as yamlLoad } from "js-yaml";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const repoRoot = resolve(webRoot, "..", "..");
const contentDir = join(repoRoot, "content");
const photosDir = join(repoRoot, "photos");
const outDir = join(webRoot, "generated");
const publicPhotos = join(webRoot, "public", "photos");
const publicIcons = join(webRoot, "public", "icons");

// Roles a person can see in the app. Benchmark photos stay on the server side.
const SHOWN_ROLES = new Set(["warmup", "lesson", "practice", "test"]);

function readYaml(path) {
  return yamlLoad(readFileSync(path, "utf8")) ?? {};
}

function fail(msg) {
  console.error(`build-content: ${msg}`);
  process.exit(1);
}

// A JSON encoder that matches Python's json.dumps(obj, sort_keys=True, default=str) byte for byte
// for the value kinds our YAML holds (strings, ints, floats, booleans, null, lists, dicts).
// core/content_loader.py computes the content hash this way, so the browser and the server agree.
function pyEscape(s) {
  let out = '"';
  for (const ch of s) {
    const cp = ch.codePointAt(0);
    if (ch === '"') out += '\\"';
    else if (ch === "\\") out += "\\\\";
    else if (ch === "\n") out += "\\n";
    else if (ch === "\r") out += "\\r";
    else if (ch === "\t") out += "\\t";
    else if (ch === "\b") out += "\\b";
    else if (ch === "\f") out += "\\f";
    else if (cp < 0x20 || cp > 0x7e) {
      if (cp > 0xffff) {
        const v = cp - 0x10000;
        const hi = 0xd800 + (v >> 10);
        const lo = 0xdc00 + (v & 0x3ff);
        out += `\\u${hi.toString(16).padStart(4, "0")}\\u${lo.toString(16).padStart(4, "0")}`;
      } else {
        out += `\\u${cp.toString(16).padStart(4, "0")}`;
      }
    } else out += ch;
  }
  return out + '"';
}

function pyDumps(v) {
  if (v === null || v === undefined) return "null";
  if (v === true) return "true";
  if (v === false) return "false";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return String(v);
    return String(v);
  }
  if (typeof v === "string") return pyEscape(v);
  if (Array.isArray(v)) return `[${v.map(pyDumps).join(", ")}]`;
  if (v instanceof Date) return pyEscape(v.toISOString());
  const keys = Object.keys(v).sort();
  return `{${keys.map((k) => `${pyEscape(k)}: ${pyDumps(v[k])}`).join(", ")}}`;
}

function contentHash(parts) {
  const h = createHash("sha256");
  for (const name of ["features", "form", "test_items", "followups", "locale", "lessons"]) {
    h.update(pyDumps(parts[name]));
  }
  return h.digest("hex").slice(0, 16);
}

// Small CSV reader that respects double quotes.
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else quoted = false;
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      field = "";
      if (row.some((f) => f !== "")) rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== "" || row.length) {
    row.push(field);
    if (row.some((f) => f !== "")) rows.push(row);
  }
  const [header, ...body] = rows;
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ""])));
}

// Minimal PNG writer for the app icon: a solid square with a lighter disc. Not a photo.
function crc32(buf) {
  let c;
  const table = [];
  for (let n = 0; n < 256; n++) {
    c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  let crc = 0xffffffff;
  for (const b of buf) crc = table[(crc ^ b) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const typeBuf = Buffer.from(type, "ascii");
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])));
  return Buffer.concat([len, typeBuf, data, crc]);
}

function iconPng(size) {
  // --ink and --bg from apps/web/styles/tokens.css. design-check keeps them honest.
  const bg = [0x14, 0x21, 0x1e];
  const fg = [0xf4, 0xf6, 0xf5];
  const raw = Buffer.alloc((size * 3 + 1) * size);
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.3;
  const r2 = size * 0.12;
  for (let y = 0; y < size; y++) {
    raw[y * (size * 3 + 1)] = 0;
    for (let x = 0; x < size; x++) {
      const dx = x + 0.5 - cx;
      const dy = y + 0.5 - cy;
      const d = Math.sqrt(dx * dx + dy * dy);
      // A ring: a plain shape for the home screen, nothing that could pass for a creek.
      const inRing = d <= r && d >= r - r2;
      const px = inRing ? fg : bg;
      const o = y * (size * 3 + 1) + 1 + x * 3;
      raw[o] = px[0];
      raw[o + 1] = px[1];
      raw[o + 2] = px[2];
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // colour type RGB
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", deflateSync(raw)),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

function main() {
  for (const p of [contentDir, photosDir, join(contentDir, "locales", "en.json"), join(photosDir, "manifest.csv")]) {
    if (!existsSync(p)) fail(`missing ${p}`);
  }
  const features = readYaml(join(contentDir, "features.yaml")).features ?? [];
  const form = readYaml(join(contentDir, "form.yaml"));
  const testItemsFile = readYaml(join(contentDir, "test_items.yaml"));
  const testItems = testItemsFile.items ?? [];
  const warmup = testItemsFile.warmup ?? [];
  const followups = readYaml(join(contentDir, "followups.yaml"));
  const locale = JSON.parse(readFileSync(join(contentDir, "locales", "en.json"), "utf8"));
  const glossary = readYaml(join(contentDir, "glossary.yaml")).terms ?? [];
  const lessons = {};
  for (const f of readdirSync(join(contentDir, "lessons")).sort()) {
    if (f.endsWith(".yaml")) lessons[f.replace(/\.yaml$/, "")] = readYaml(join(contentDir, "lessons", f));
  }
  const regions = {};
  for (const f of readdirSync(join(contentDir, "regions")).sort()) {
    if (f.endsWith(".yaml")) regions[f.replace(/\.yaml$/, "")] = readYaml(join(contentDir, "regions", f));
  }

  // Hash first, over the full content, so it matches the server. Then strip.
  const content_hash = contentHash({ features, form, test_items: testItems, followups, locale, lessons });

  const consentKeys = Object.keys(locale).filter((k) => k.startsWith("consent.")).sort();
  const consent_version = "en-" + createHash("sha256").update(consentKeys.map((k) => `${k}=${locale[k]}`).join("\n")).digest("hex").slice(0, 12);

  const manifestRows = parseCsv(readFileSync(join(photosDir, "manifest.csv"), "utf8"));
  const photos = {};
  const copyList = [];
  for (const row of manifestRows) {
    if (!row.id || !row.file) continue;
    if (!SHOWN_ROLES.has(row.role)) continue;
    const src = join(photosDir, row.file);
    if (!existsSync(src)) fail(`manifest row ${row.id} points at a missing file ${row.file}`);
    const isPlaceholder = row.license === "placeholder";
    const file = basename(row.file);
    photos[row.id] = {
      id: row.id,
      file,
      url: `/photos/${file}`,
      role: row.role,
      feature: row.feature || null,
      placeholder: isPlaceholder,
      // Alt text never gives away a test answer. Placeholders say what they are; a real photo gets a
      // neutral scene line unless the manifest grows an `alt` column.
      alt: isPlaceholder ? locale["photo.placeholder_alt"] : row.alt || locale["photo.creek_alt"],
      // CC BY and CC BY-SA ask us to name the author wherever the photo appears, so the credit
      // travels with the photo into the browser and /credits lists every one of them.
      author: row.author || "",
      license: row.license || "",
      source_url: row.source_url || "",
      // width and height keep layout stable while the image loads
      width: 1200,
      height: 900,
    };
    copyList.push({ src, file });
  }

  // Fail the build rather than publish a CC BY photo with nobody's name on it.
  const unattributed = Object.values(photos).filter(
    (p) => p.license.startsWith("CC-BY") && !p.author.trim(),
  );
  if (unattributed.length) {
    fail(`these photos need an author for their licence: ${unattributed.map((p) => `${p.id} (${p.license})`).join(", ")}`);
  }

  const strippedItems = testItems.map(({ id, feature, photo_id }) => {
    if (!photos[photo_id]) fail(`test item ${id} uses photo ${photo_id} that is not shown`);
    return { id, feature, photo_id };
  });
  for (const w of warmup) if (!photos[w.photo_id]) fail(`warmup ${w.id} uses unknown photo ${w.photo_id}`);
  if (warmup.filter((w) => w.more_natural === true).length !== 1) fail("exactly one warm-up photo must be more_natural");
  for (const [fid, lesson] of Object.entries(lessons)) {
    for (const pair of lesson.contrast_pairs ?? []) {
      for (const pid of [pair.assume_photo_id, pair.actual_photo_id]) {
        if (!photos[pid]) fail(`lesson ${fid} uses unknown photo ${pid}`);
      }
    }
    if (lesson.practice && !photos[lesson.practice.photo_id]) fail(`lesson ${fid} practice photo missing`);
  }

  const generated = {
    generated_at: new Date().toISOString(),
    content_hash,
    consent_version,
    features,
    form,
    test_items: strippedItems,
    // more_natural travels with the pair so the reveal can badge the right photo wherever it
    // sits. It is not an answer to a scored item, so it gives nothing away before the test.
    warmup: warmup.map(({ id, photo_id, more_natural }) => ({ id, photo_id, more_natural: more_natural === true })),
    followups: { max_questions: followups.max_questions ?? 2 },
    glossary,
    regions,
    lessons,
    locale,
    photos,
  };

  // Guard: nothing named gold may remain anywhere in the output.
  const text = JSON.stringify(generated, null, 2);
  if (/"gold(_label)?"\s*:/.test(text.replace(/"practice":\s*\{[^}]*\}/g, ""))) {
    fail("a gold label leaked into generated content");
  }

  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "content.json"), text + "\n");

  rmSync(publicPhotos, { recursive: true, force: true });
  mkdirSync(publicPhotos, { recursive: true });
  for (const { src, file } of copyList) copyFileSync(src, join(publicPhotos, file));

  mkdirSync(publicIcons, { recursive: true });
  writeFileSync(join(publicIcons, "icon-192.png"), iconPng(192));
  writeFileSync(join(publicIcons, "icon-512.png"), iconPng(512));

  const precache = {
    version: content_hash,
    pages: ["/", "/t", "/demo", "/check", "/about", "/privacy", "/how-we-know", "/offline", "/manifest.webmanifest"],
    photos: Object.values(photos).map((p) => p.url),
  };
  writeFileSync(join(webRoot, "public", "precache.json"), JSON.stringify(precache, null, 2) + "\n");

  // Stamp the service worker cache name with the content hash so a content swap really lands.
  const swPath = join(webRoot, "public", "sw.js");
  const sw = readFileSync(swPath, "utf8");
  const stamped = sw.replace(/const VERSION = "[^"]*";/, `const VERSION = "sl-${content_hash}";`);
  if (stamped !== sw) writeFileSync(swPath, stamped);

  const size = statSync(join(outDir, "content.json")).size;
  console.log(`build-content: content_hash ${content_hash}, consent ${consent_version}, ${copyList.length} photos copied, content.json ${size} bytes`);
}

main();
