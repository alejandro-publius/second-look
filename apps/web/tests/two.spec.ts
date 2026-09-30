import { expect, test } from "@playwright/test";
import { exampleLabComponents, mockApi } from "./mock-api.mjs";

// Audit findings api-fhir-1 and docs-consistency-2: the lab record their sandbox gives has no
// single value and no one moment. It has five figures for a year, each a component, a period and a
// performer named by display. The card showed "Value none" and "When none" for it, and "A lab" in
// place of the name the record gives. The mock has the record's shape with made-up numbers.
test("/two shows a lab record's components, its period and its performer, and never the word none", async ({ page }) => {
  await mockApi(page, { theirsShape: "components", theirsStatus: "cached" });
  await page.goto("/two");
  const lab = page.getByRole("region", { name: "Lab (OneAquaHealth sandbox)" });
  await expect(lab).toBeVisible();
  const field = (name: string) => lab.locator("dl > div").filter({ has: page.locator("dt", { hasText: new RegExp(`^${name}$`) }) }).locator("dd");

  // Every component, in the record's order, as the record gives it: name, number, unit.
  await expect(field("Value")).toHaveText(
    exampleLabComponents.component.map((c) => `${c.code.coding[0].display} ${c.valueQuantity.value} ${c.valueQuantity.unit}`),
  );
  await expect(field("Value")).toHaveCount(5);
  await expect(field("Value").first()).toHaveText("Average 7.4 milligram per liter");
  await expect(field("Value").nth(3)).toHaveText("Standard Deviation 0.85 milligram per liter");

  // The period, both ends, with no day slipped by the reader's time zone.
  await expect(field("When")).toHaveText("Jan 1, 2020 to Dec 31, 2020");
  // The name their record gives its performer, not our fixed word for one.
  await expect(field("Performer")).toHaveText("A government chemical service");
  await expect(field("What was measured")).toHaveText("Dissolved Oxygen");

  await expect(lab.locator("dd").filter({ hasText: /^none$/ })).toHaveCount(0);
  await expect(lab.locator("dl")).not.toContainText(/\bnone\b/i);
  await expect(page.getByText("Fetched from their sandbox at", { exact: false })).toBeVisible();
});

// The card is shared, so the records it showed well before must read as they did: one value at
// one moment, and our fixed words where a record gives its performer no name.
test("/two still shows a plain value, a single moment and the fixed performer words", async ({ page }) => {
  await mockApi(page);
  await page.goto("/two");
  const lab = page.getByRole("region", { name: "Lab (OneAquaHealth sandbox)" });
  const ours = page.getByRole("region", { name: "Volunteer (Second Look)" });
  const field = (card: typeof lab, name: string) =>
    card.locator("dl > div").filter({ has: page.locator("dt", { hasText: new RegExp(`^${name}$`) }) }).locator("dd");
  await expect(field(lab, "Value")).toHaveText(["Present"]);
  await expect(field(ours, "Value")).toHaveText(["Present"]);
  await expect(field(lab, "When")).toContainText("Sep 23, 2026");
  await expect(field(lab, "Performer")).toHaveText("A lab");
  await expect(field(ours, "Performer")).toHaveText("A volunteer");
});
