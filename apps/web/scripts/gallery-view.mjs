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
