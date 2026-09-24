// Smaller AVIF and WebP copies of a photo, from photos/derived/manifest.csv, which
// scripts/derive_photos.py writes (Update 22 section 1 answer 2). Only the two warm-up photos
// have copies. A photo without copies gets nothing here, so its <img> stays exactly as it was.
// build-content.mjs puts the result into content.json; components/Photo.tsx and photoPreloads()
// in security-headers.mjs read it from there, so the page and the Early Hints say the same thing.

// Best first: a browser takes the first <source> whose type it can show.
export const SOURCE_TYPES = { avif: "image/avif", webp: "image/webp" };

// How wide the photo is drawn, which is what sizes has to describe. Both pages crop with
// object-fit: cover, so a wide photo is drawn wider than its frame. On a phone the landing frame
// is 3 by 4 and about 43 per cent of the screen, so the 1600 by 1080 photo is drawn 84 to 90 per
// cent of the screen wide. From 900 pixels up the frame is 4 by 3 and at most 550 wide, which
// draws that photo 611 wide. The poster draws them smaller, so it asks for a little more than it
// needs, which is fine for print.
export const DERIVED_SIZES = "(min-width: 900px) 612px, 90vw";

/**
 * For each source photo id with copies: the <source> list, the sizes that go with it and the
 * files to copy into public/photos. Throws when a copy was made from another version of its
 * photo, so a stale copy can never ship.
 */
export function derivedSources(manifestRows, derivedRows) {
  const byId = new Map(manifestRows.filter((r) => r.id).map((r) => [r.id, r]));
  const grouped = new Map();
  for (const row of derivedRows) {
    const source = byId.get(row.source_id);
    if (!source) throw new Error(`copy ${row.file} names ${row.source_id}, which has no manifest row`);
    if (source.sha256 !== row.source_sha256) throw new Error(`copy ${row.file} was made from another version of ${row.source_id}`);
    if (!SOURCE_TYPES[row.format]) throw new Error(`copy ${row.file} has unknown format ${row.format}`);
    if (!grouped.has(row.source_id)) grouped.set(row.source_id, []);
    grouped.get(row.source_id).push(row);
  }
  const out = {};
  for (const [id, rows] of grouped) {
    const sources = Object.keys(SOURCE_TYPES)
      .map((fmt) => {
        const set = rows.filter((r) => r.format === fmt).sort((a, b) => Number(a.width) - Number(b.width));
        if (!set.length) return null;
        const url = (r) => `/photos/${r.file.split("/").pop()}`;
        return { type: SOURCE_TYPES[fmt], srcset: set.map((r) => `${url(r)} ${Number(r.width)}w`).join(", ") };
      })
      .filter(Boolean);
    out[id] = { sources, sizes: DERIVED_SIZES, files: rows.map((r) => r.file) };
  }
  return out;
}

/** The first URL in a srcset: the smallest copy, the cheapest one to fetch by mistake. */
export function firstUrl(srcset) {
  return srcset.split(",")[0].trim().split(/\s+/)[0];
}
