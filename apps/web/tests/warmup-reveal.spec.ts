import { expect, test } from "@playwright/test";
import { content, moreNatural, type WarmupItem } from "../lib/content";

// The reveal answers the poster's question on the end screen, after the test. It must never say
// "the one on the right": on a phone the two photographs stack, and the order they were shown in
// may be shuffled (Update 11D item 1). These tests pin that down from both ends.

test.describe("the warm-up reveal does not depend on the order", () => {
  test("exactly one of the pair is the more natural creek, in either order", () => {
    const [a, b] = content.warmup;
    expect(content.warmup.filter((w) => w.more_natural)).toHaveLength(1);

    const forward = moreNatural([a, b]);
    const reversed = moreNatural([b, a]);
    expect(forward?.photo_id).toBe(reversed?.photo_id);
    expect(forward?.id).toBe(reversed?.id);
  });

  test("shuffling the pair never moves the badge to the other photo", () => {
    const orders: WarmupItem[][] = [content.warmup, [...content.warmup].reverse()];
    const picked = orders.map((order) => {
      // What the component renders: the badge goes on the item carrying more_natural, and the
      // other note goes on the one that does not, whichever position each of them is in.
      const badged = order.filter((w) => w.more_natural);
      const plain = order.filter((w) => !w.more_natural);
      expect(badged).toHaveLength(1);
      expect(plain).toHaveLength(1);
      return { badge: badged[0].photo_id, other: plain[0].photo_id };
    });
    expect(picked[0]).toEqual(picked[1]);
    expect(picked[0].badge).not.toBe(picked[0].other);
  });

  test("no reveal string names a side", () => {
    for (const key of [
      "warmup.reveal_point",
      "warmup.reveal_badge",
      "warmup.reveal_other",
      "warmup.reveal_natural_note",
      "warmup.reveal_modified_note",
      "warmup.reveal_limit",
    ]) {
      const value = content.locale[key];
      expect(value, key).toBeTruthy();
      expect(value.toLowerCase(), key).not.toMatch(/\b(left|right)\b/);
    }
  });
});
