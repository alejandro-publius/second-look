import { content } from "@/lib/content";

// The share card image, built from the score number alone. No personal data goes in, so a forged
// score is harmless. Text comes from the locale like every other string.
const TOTAL = 16;

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function fill(key: string, params: Record<string, string | number>): string {
  const s = content.locale[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (w, k: string) => (k in params ? String(params[k]) : w));
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
    const filled = Math.round((n / TOTAL) * 1000);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-label="${esc(line1)}">
<rect width="1200" height="630" fill="#fbfaf6"/>
<rect x="0" y="0" width="1200" height="18" fill="#1f3a2e"/>
<text x="100" y="230" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif" font-size="88" font-weight="700" fill="#14211b">${esc(line1)}</text>
<rect x="100" y="290" width="1000" height="28" rx="14" fill="#d9d9d9"/>
<rect x="100" y="290" width="${filled}" height="28" rx="14" fill="#1f3a2e"/>
<text x="100" y="400" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif" font-size="44" fill="#465850">${esc(line2)}</text>
<text x="100" y="540" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif" font-size="36" font-weight="700" fill="#1f3a2e">${esc(line3)}</text>
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
