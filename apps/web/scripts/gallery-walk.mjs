// How the gallery answers a walk before it shows the walk's city view. scripts/gallery.mjs uses it,
// and tests/walk.spec.ts runs it, so a change here is tested.
//
// The clips show natural creeks. The gallery once tapped the first button on every screen, which
// answers Yes to every yes or no question, so its picture of the city view showed dams, pipes and
// plants the clip does not show (CRITIC_09 Q01). Now each answer is chosen on purpose: the bank as
// asked, and no other damage anywhere.

/**
 * Answers the walk on screen, from the question it is on, until its record shows: `bank` (an
 * answer value, "present" or "absent") on the bank question, No on every yes or no question, None
 * of these on a list, Skip on a number, Next on the feelings, and the first choice on any other
 * choice. The first choices say nothing is wrong: Flat, Natural, Fast, Clear, Herbs and Good.
 *
 * The follow-up questions the rules ask after the form (judge walk W01) are left unanswered with
 * Finish, like the checker's question, unless `until` is "followups", which stops on them.
 *
 * @param {import("@playwright/test").Page} page
 * @param {any} content the generated content.json, for the form and the words on its buttons
 * @param {{ bank: "present" | "absent", until?: "record" | "followups" }} how
 */
export async function answerWalkPlainly(page, content, { bank, until = "record" }) {
  const say = (key) => content.locale[key];
  const items = content.form.items;
  const bankItem = items.find((i) => i.feature === "artificial_bank");
  const bankLabel = bankItem.options.find((o) => o.value === bank).label;
  const exact = (name) => page.getByRole("button", { name, exact: true });
  const done = page.getByRole("heading", { name: say("walk.done_title"), level: 1 });
  const followups = page.getByTestId("walk-followups");
  for (let i = 0; i < 60; i++) {
    if (await done.isVisible()) return;
    if (until === "followups" && (await followups.isVisible())) return;
    // The follow-ups, or the checker's question, after the form: nothing to answer there.
    if (await exact(say("check.finish")).isVisible()) {
      await exact(say("check.finish")).click();
      continue;
    }
    const question = (await page.locator("h1#question").innerText()).trim();
    // A question with a unit shows it after the text: "Water height in metres (m)".
    const item = items.find((it) => question === (it.unit ? `${it.text} (${it.unit})` : it.text));
    if (!item) throw new Error(`answerWalkPlainly: no form item reads "${question}"`);
    if (item.id === bankItem.id) await exact(bankLabel).click();
    else if (item.type === "yesno") await exact(say("check.no")).click();
    else if (item.type === "multi" || item.type === "pick_region_list") await exact(say("check.none_of_these")).click();
    else if (item.type === "number") await exact(say("check.skip")).click();
    else if (item.type === "sliders") await exact(say("check.next")).click();
    else await page.getByRole("main").getByRole("group").first().getByRole("button").first().click();
    // On to the next screen before the next look: the question on screen has changed or gone.
    await page.waitForFunction((q) => document.querySelector("h1#question")?.textContent?.trim() !== q, question);
  }
  await done.waitFor();
}
