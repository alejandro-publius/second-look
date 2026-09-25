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
 */
export async function toRegionTop(page, name) {
  const region = page.getByRole("region", { name });
  await region.waitFor();
  const y = await region.evaluate((el) => Math.max(0, Math.round(el.getBoundingClientRect().top + window.scrollY - 12)));
  await page.evaluate((top) => window.scrollTo(0, top), y);
  await page.waitForFunction((top) => Math.abs(window.scrollY - Math.min(top, document.documentElement.scrollHeight - window.innerHeight)) < 2, y);
}
