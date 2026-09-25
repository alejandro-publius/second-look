// Where the gallery stands on a page before it takes a shot. scripts/gallery.mjs uses it, and
// tests/walk.spec.ts runs it on a walk's record, so a change here is tested.

/**
 * Goes to the top of the page and waits until it is there, so the shot opens on the page title.
 * A walk's record shows wherever the long form before it left the page, and a shot from there
 * opened on a line cut in half, with the title out of the frame (CRITIC_06 H03).
 */
export async function toPageTop(page) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForFunction(() => window.scrollY === 0);
}

/**
 * Goes to the top of the page and fails unless the element is whole on that first screen. Returns
 * its box. The gallery's picture of a walk says it shows a button to start the check, and a note
 * above the button once pushed it below the first screen, so the picture showed none (CRITIC_11 V01).
 */
export async function wholeOnFirstScreen(page, locator) {
  await locator.waitFor();
  await page.evaluate(() => document.fonts.ready);
  await toPageTop(page);
  const box = await locator.boundingBox();
  const height = page.viewportSize().height;
  if (!box || box.y < 0 || box.y + box.height > height) {
    const where = box ? `from ${Math.round(box.y)} to ${Math.round(box.y + box.height)}` : "not drawn";
    throw new Error(`gallery-view: the element is not whole on the first screen (${where}, screen ${height} tall)`);
  }
  return box;
}

/**
 * Puts the top of a named region at the top of the screen, so the shot shows that region from its
 * heading down. The walk's city view listed a plant above its needs, and a shot from the page top
 * cut the first measure off before its source (CRITIC_07 J04).
 *
 * When the page is too short to bring the region that far up, it stops at the top of a whole line
 * or block above it instead. Stopping where the page ends cut the walk's city view through the
 * middle of a line of text at the top edge (CRITIC_11 U02).
 */
export async function toRegionTop(page, name) {
  const region = page.getByRole("region", { name });
  await region.waitFor();
  await page.evaluate(() => document.fonts.ready);
  const y = await region.evaluate((el) => {
    const GAP = 12;
    const scrolled = window.scrollY;
    const want = Math.max(0, el.getBoundingClientRect().top + scrolled - GAP);
    const most = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    if (want <= most) return Math.round(want);
    // What an edge must not cut, in page coordinates: every line of text, and every drawn block
    // shorter than the screen (a picture, a notice, a card, a button).
    const boxes = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (!n.textContent || !n.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(n);
      for (const r of Array.from(range.getClientRects())) if (r.height > 1) boxes.push([r.top + scrolled, r.bottom + scrolled]);
    }
    for (const e of Array.from(document.body.querySelectorAll("*"))) {
      const r = e.getBoundingClientRect();
      if (r.height <= 1 || r.height >= window.innerHeight) continue;
      const s = getComputedStyle(e);
      if (s.visibility === "hidden" || s.display === "none") continue;
      const media = ["IMG", "VIDEO", "SVG", "CANVAS", "PICTURE"].includes(e.tagName.toUpperCase());
      const drawn = s.backgroundColor !== "rgba(0, 0, 0, 0)" || parseFloat(s.borderTopWidth) > 0 || parseFloat(s.borderBottomWidth) > 0;
      if (media || drawn) boxes.push([r.top + scrolled, r.bottom + scrolled]);
    }
    // An edge at `top` cuts a box when more than a pixel of it is on each side.
    const cutAt = (top) => boxes.filter(([a, b]) => a < top - 1 && top + 1 < b);
    let top = most;
    for (let i = 0; i < boxes.length + 1; i++) {
      const cut = cutAt(top);
      if (cut.length === 0) break;
      // Up to the top of the highest box it cuts, with a small gap when the gap cuts nothing above.
      const from = Math.min(...cut.map(([a]) => a));
      const above = boxes.filter(([, b]) => b <= from + 1).map(([, b]) => b);
      top = Math.max(0, from - GAP, ...above);
    }
    return Math.round(top);
  });
  await page.evaluate((top) => window.scrollTo(0, top), y);
  await page.waitForFunction((top) => Math.abs(window.scrollY - top) < 2, y);
}
