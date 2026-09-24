import type { Metadata } from "next";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("a11y.title")}: ${t("app.name")}` };

// What we aim for and how we check it. Every sentence here is true of the code: the checks it
// names are apps/web/tests/axe.spec.ts, keyboard.spec.ts and reflow.spec.ts, the design check in
// apps/web/scripts/design-check.mjs, and scripts/check_readability.py.
export default function AccessibilityPage() {
  return (
    <article className="stack">
      <h1>{t("a11y.title")}</h1>
      <p>{t("a11y.intro")}</p>
      <h2>{t("a11y.checked_title")}</h2>
      <ul>
        <li>{t("a11y.checked_axe")}</li>
        <li>{t("a11y.checked_keyboard")}</li>
        <li>{t("a11y.checked_reflow")}</li>
        <li>{t("a11y.checked_tap")}</li>
        <li>{t("a11y.checked_contrast")}</li>
        <li>{t("a11y.checked_motion")}</li>
        <li>{t("a11y.checked_words")}</li>
        <li>{t("a11y.checked_alt")}</li>
      </ul>
      <h2>{t("a11y.limits_title")}</h2>
      <p>{t("a11y.limits_body")}</p>
      <h2>{t("a11y.tell_title")}</h2>
      <p className="small muted">{t("consent.contact")}</p>
    </article>
  );
}
