import { CARD_FLAG, CARD_FONT, CARD_INK, CARD_INK_SOFT, CARD_LINE, CARD_SURFACE } from "@/app/theme";
import { content } from "@/lib/content";

// The share card image, built from the score number alone. No personal data goes in, so a forged
// score is harmless. Text comes from the locale like every other string.
//
// This is the only artefact that leaves the product, so it is the staff gauge at poster size:
// sixteen square blocks, filled left to right, the same object as the progress bar in the test and
// the score mark on a record. Colours come from app/theme.ts, which mirrors the tokens. The font
// is named rather than embedded, because an SVG served as an image cannot load one from us; where
// it is missing the renderer falls back and the card still reads.
const TOTAL = 16;
const BLOCK_W = 55;
const BLOCK_H = 28;
const GAP = 8;
const LEFT = 100;
const TOP = 290;

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function fill(key: string, params: Record<string, string | number>): string {
  const s = content.locale[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (w, k: string) => (k in params ? String(params[k]) : w));
}

function gauge(n: number): string {
  return Array.from({ length: TOTAL }, (_, i) => {
    const x = LEFT + i * (BLOCK_W + GAP);
    const full = i < n;
    return `<rect x="${x}" y="${TOP}" width="${BLOCK_W}" height="${BLOCK_H}" fill="${full ? CARD_FLAG : CARD_SURFACE}" stroke="${CARD_LINE}" stroke-width="1"/>`;
  }).join("");
}

export function GET(_req: Request, ctx: { params: Promise<{ score: string }> }) {
  return ctx.params.then(({ score }) => {
    const n = Number(score);
    if (!/^\d{1,2}$/.test(score) || !Number.isInteger(n) || n < 0 || n > TOTAL) {
      return new Response("not found", { status: 404 });
    }
    const line1 = fill("share.card_line1", { correct: n, total: TOTAL });
    const line2 = content.locale["share.card_line2"] ?? "";
    const line3 = content.locale["app.name"] ?? "Second Look";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-label="${esc(line1)}">
<rect width="1200" height="630" fill="${CARD_SURFACE}"/>
<rect x="0" y="0" width="1200" height="18" fill="${CARD_FLAG}"/>
<text x="100" y="230" font-family="${CARD_FONT}" font-size="88" font-weight="700" fill="${CARD_INK}">${esc(line1)}</text>
${gauge(n)}
<text x="100" y="420" font-family="${CARD_FONT}" font-size="44" fill="${CARD_INK_SOFT}">${esc(line2)}</text>
<text x="100" y="540" font-family="${CARD_FONT}" font-size="36" font-weight="700" fill="${CARD_INK}">${esc(line3)}</text>
</svg>`;
    return new Response(svg, {
      status: 200,
      headers: {
        "content-type": "image/svg+xml; charset=utf-8",
        "cache-control": "public, max-age=86400, immutable",
      },
    });
  });
}
