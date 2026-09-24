// After a build: the landing page and the poster preload the same photo copies their <picture>
// shows, and public/_headers preloads the same set again as the Link header. Two code paths write
// these (React's preload in components/Photo.tsx, photoPreloads() in security-headers.mjs), and if
// they drift a phone fetches two copies of one photo, or the JPEG as well (Update 22 section 1).
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { linkEntry, photoPreloads } from "../security-headers.mjs";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const content = JSON.parse(readFileSync(join(web, "generated", "content.json"), "utf8"));
const headers = readFileSync(join(web, "public", "_headers"), "utf8");
const pages = { "/": ["index.html"], "/poster": ["poster.html"] };
// The newest build only: a static export and a server build can sit side by side, and an old one
// would be checked against today's content.
const built = [join(web, "out"), join(web, ".next", "server", "app")].filter((p) => existsSync(join(p, "index.html")));
const roots = built.sort((a, b) => statSync(join(b, "index.html")).mtimeMs - statSync(join(a, "index.html")).mtimeMs).slice(0, 1);
if (!roots.length) {
  console.log("check-preloads: no built pages to read; run the build first");
  process.exit(1);
}

const attrs = (tag) => Object.fromEntries([...tag.matchAll(/([a-zA-Z-]+)="([^"]*)"/g)].map((m) => [m[1].toLowerCase(), m[2].replaceAll("&amp;", "&")]));
const problems = [];
let checked = 0;
const expected = photoPreloads(content);
for (const root of roots) {
  for (const [path, [file]] of Object.entries(pages)) {
    const html = readFileSync(join(root, file), "utf8");
    const preloads = [...html.matchAll(/<link [^>]*rel="preload"[^>]*>/g)].map((m) => attrs(m[0])).filter((a) => a.as === "image");
    const sources = [...html.matchAll(/<source [^>]*>/g)].map((m) => attrs(m[0]));
    for (const want of expected[path] ?? []) {
      const where = `${root.slice(web.length + 1)}/${file}`;
      if (!want.imagesrcset) {
        if (!preloads.some((p) => p.href === want.href)) problems.push(`${where}: no preload of ${want.href}`);
        continue;
      }
      const page = preloads.filter((p) => p.imagesrcset === want.imagesrcset);
      if (page.length !== 1 || page[0].imagesizes !== want.imagesizes || page[0].type !== want.type || page[0].href) {
        problems.push(`${where}: the page's own preload of ${want.href} differs from the Link header`);
      }
      if (!sources.some((s) => s.type === want.type && s.srcset === want.imagesrcset && s.sizes === want.imagesizes)) {
        problems.push(`${where}: the <picture> does not offer the AVIF set that is preloaded`);
      }
      const photo = Object.values(content.photos).find((p) => p.sources?.some((s) => s.srcset === want.imagesrcset));
      if (photo && preloads.some((p) => p.href === photo.url)) problems.push(`${where}: still preloads the JPEG ${photo.url}`);
    }
    const line = `\n${path}\n  Link: ${(expected[path] ?? []).map(linkEntry).join(", ")}\n`;
    if (expected[path] && !headers.includes(line)) problems.push(`public/_headers: the Link header for ${path} is not what the content says`);
    checked += 1;
  }
}
if (problems.length) {
  console.log(problems.join("\n"));
  console.log(`check-preloads: ${problems.length} problem(s)`);
  process.exit(1);
}
console.log(`check-preloads: ${checked} page(s), each preloads the copies it shows and matches public/_headers`);
