// What iNaturalist itself said about each of its photos we show, from results/inat_photos.json
// (scripts/verify_inat_photos.py), for the credits page. Only three facts per photo travel to the
// browser: still there or not, research grade or not, inside California or not. The species and
// the place stay out, because a test photo's species is its answer.
// scripts/tests/test_inaturalist.py runs this with a record that carries both and checks.

/** @param {any} raw the parsed results file, or null. @param {Set<string>} shown photo ids. */
export function inatChecks(raw, shown) {
  const out = { checked_at: String(raw?.checked_at ?? ""), photos: {} };
  for (const p of raw?.photos ?? []) {
    if (!shown.has(p.photo_id)) continue;
    out.photos[p.photo_id] = { found: p.found === true, research_grade: p.research_grade === true, in_california: p.in_california === true };
  }
  return out;
}
