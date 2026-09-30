// The one definition of our security headers. next.config.ts uses it for the server build and
// scripts/build-headers.mjs writes the same thing into public/_headers for Cloudflare Pages,
// which serves a static export and so gets no headers from Next at all.
import { firstUrl } from "./photo-sources.mjs";

// Cloudflare Pages reads at most this many characters on one line of _headers.
export const HEADERS_LINE_LIMIT = 2000;
// And at most this many rules in the whole file.
export const HEADERS_RULE_LIMIT = 100;
// The share cards are /api/share/0 up to this number, one for each score a person can get. It is
// TOTAL in app/api/share/[score]/route.ts, and scripts/tests/test_web_headers.py holds the two
// together.
export const SHARE_CARD_TOTAL = 16;

/**
 * True when the API origin is an address on this machine or on the local network. Only a test
 * or development build has one, and Cloudflare Pages could never reach it.
 */
export function isLocalOrigin(origin) {
  if (!origin) return false;
  let host;
  try {
    host = new URL(origin).hostname.toLowerCase();
  } catch {
    return false;
  }
  if (host === "localhost" || host.endsWith(".localhost")) return true;
  if (host === "[::1]" || host === "::1" || host === "0.0.0.0") return true;
  const part = host.split(".").map(Number);
  if (part.length !== 4 || part.some((n) => !Number.isInteger(n))) return false;
  const [a, b] = part;
  return a === 127 || a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 169 && b === 254);
}

export function buildHeaders({ apiOrigin, isDev = false }) {
  // Next's App Router hydrates through inline <script> tags it writes itself, so script-src needs
  // 'unsafe-inline'; a nonce would force every page to render per request and the landing page
  // must stay static. 'unsafe-eval' is development only. Styles come from our own CSS files only.
  // An empty apiOrigin means the API is served under /api/* on this same origin (Update 10 A1),
  // so the browser may connect to 'self' and nowhere else.
  const connect = apiOrigin ? `connect-src 'self' ${apiOrigin}` : "connect-src 'self'";
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
    `style-src 'self'${isDev ? " 'unsafe-inline'" : ""}`,
    "img-src 'self' data: blob:",
    connect,
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "manifest-src 'self'",
    "worker-src 'self'",
  ].join("; ");

  const everywhere = [
    { key: "Content-Security-Policy", value: csp },
    { key: "Referrer-Policy", value: "no-referrer" },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "X-Frame-Options", value: "DENY" },
    // Only the creek check and the quick return check ask for location or a camera photo, but a
    // permissions policy belongs to the page that was loaded, and a tap on a Next link loads none.
    // With geolocation=() here, a check opened from /judges could never find the phone's position
    // and said the person had refused (CRITIC_09 R01). So every page allows our own origin, and
    // every other feature stays off.
    { key: "Permissions-Policy", value: "geolocation=(self), camera=(self), microphone=(), payment=(), usb=()" },
  ];

  return { csp, everywhere };
}

/**
 * The pages that preload photos, and which. The landing page and the poster show the two warm-up
 * photos first. Pages turns a Link header into an Early Hint, so the photos start loading before
 * the page arrives. Pages used to write these headers itself from the page's own preload tags,
 * but stopped once the project gained the /api Functions, and the first screen got slower.
 */
export function photoPreloads(content) {
  // The first photo is the page's largest paint (Lighthouse, 2026-09-24), so its preload asks for
  // high priority, as its <img> does: both photos load at once, and the first should not wait.
  const links = (content?.warmup ?? [])
    .slice(0, 2)
    .map((w, i) => {
      const entry = photoPreload(content?.photos?.[w.photo_id]);
      return entry && i === 0 ? { ...entry, fetchpriority: "high" } : entry;
    })
    .filter(Boolean);
  return links.length ? { "/": links, "/poster": links } : {};
}

/**
 * One preload per photo. A photo with smaller copies preloads its AVIF set exactly as the page's
 * own preload tag does: imagesrcset and imagesizes, so the browser fetches only the copy it will
 * show, and type, so a browser without AVIF fetches none of them, and no phone gets the JPEG too.
 * Chrome skips a preload like this in a 103 Early Hint and acts on it once the page's own response
 * arrives. A photo without copies keeps the plain preload of its URL.
 */
export function photoPreload(photo) {
  if (!photo?.url) return null;
  const avif = (photo.sources ?? []).find((s) => s.type === "image/avif");
  if (!avif) return { href: photo.url };
  return { href: firstUrl(avif.srcset), type: avif.type, imagesrcset: avif.srcset, imagesizes: photo.sizes };
}

/** One Link header entry. The attributes go in quotes, because a srcset holds commas. */
export function linkEntry(entry) {
  const { href, type, imagesrcset, imagesizes, fetchpriority } = typeof entry === "string" ? { href: entry } : entry;
  if (fetchpriority && !["high", "low", "auto"].includes(fetchpriority)) throw new Error(`a Link fetchpriority is high, low or auto: ${fetchpriority}`);
  const quoted = (name, value) => {
    if (/["\r\n]/.test(value)) throw new Error(`a Link ${name} cannot hold quotes or line breaks: ${value}`);
    return `; ${name}="${value}"`;
  };
  return (
    `<${href}>; rel=preload; as=image` +
    (type ? quoted("type", type) : "") +
    (imagesrcset ? quoted("imagesrcset", imagesrcset) : "") +
    (imagesizes ? quoted("imagesizes", imagesizes) : "") +
    (fetchpriority ? `; fetchpriority=${fetchpriority}` : "")
  );
}

/** The Cloudflare Pages _headers format: a path, then one indented header line each. */
export function headersFile({ apiOrigin, preloads = {} }) {
  // The file is tracked and only Pages reads it. A test build once left its mock API's address
  // in the committed policy line, so a local address is refused here, whoever asks.
  if (isLocalOrigin(apiOrigin)) {
    throw new Error(`public/_headers is the policy Cloudflare Pages sends, and ${apiOrigin} is a local address. A test or development build writes the file for an empty API origin.`);
  }
  const { everywhere } = buildHeaders({ apiOrigin });
  const block = (path, list) => `${path}\n${list.map((h) => `  ${h.key}: ${h.value}`).join("\n")}\n`;
  const link = (entries) => ({ key: "Link", value: entries.map(linkEntry).join(", ") });
  const text = [
    "# Generated by scripts/build-headers.mjs from security-headers.mjs. Do not edit by hand.",
    "",
    block("/*", everywhere),
    ...Object.entries(preloads).map(([path, urls]) => block(path, [link(urls)])),
    "/sw.js\n  Cache-Control: no-cache\n",
    // An OpenTimestamps proof is a small binary file. Pages guesses the type from the ending, and
    // .ots is also the ending of a spreadsheet template, so a phone offered to open a proof in a
    // spreadsheet app. Plain bytes make the browser save the file, which is what /verify asks for.
    "/proofs/*.ots\n  Content-Type: application/octet-stream\n",
    // The share cards are written as extensionless files by the static export, so Pages would
    // guess application/octet-stream and no chat window would render the preview. One rule for
    // each card that exists, and none with a star: Pages adds a rule's headers to its not found
    // page too, so /api/share/* sent the HTML of that page for /api/share/999 as an SVG image.
    ...Array.from({ length: SHARE_CARD_TOTAL + 1 }, (_, score) => `/api/share/${score}\n  Content-Type: image/svg+xml; charset=utf-8\n`),
  ].join("\n");
  // Pages drops a longer line without a word, and the Early Hints with it.
  const long = text.split("\n").find((line) => line.length > HEADERS_LINE_LIMIT);
  if (long) throw new Error(`a _headers line is ${long.length} characters, over the ${HEADERS_LINE_LIMIT} Pages reads: ${long.slice(0, 80)}`);
  const rules = text.split("\n").filter((line) => /^(\/|https:\/\/)/.test(line)).length;
  if (rules > HEADERS_RULE_LIMIT) throw new Error(`_headers holds ${rules} rules, over the ${HEADERS_RULE_LIMIT} Pages reads`);
  return text;
}
