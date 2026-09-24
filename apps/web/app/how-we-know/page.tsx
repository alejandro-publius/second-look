import type { Metadata } from "next";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("how.title")}: ${t("app.name")}` };

// The plan was tagged prereg-v1 on 2026-09-21, before any participant, and a tag is never moved
// (hard rules 13 and 15), so the page names it as made (REVIEW_03 R30).
const PLAN_TAG = process.env.NEXT_PUBLIC_PLAN_TAG || "prereg-v1";

export default function HowWeKnowPage() {
  return (
    <article className="stack">
      <h1>{t("how.title")}</h1>
      <p>{t("how.intro")}</p>
      <h2>{t("how.plan_title")}</h2>
      <p>{t("how.plan", { tag: PLAN_TAG })}</p>
      <h2>{t("how.flow_title")}</h2>
      <ol>
        <li>{t("how.flow_1")}</li>
        <li>{t("how.flow_2")}</li>
        <li>{t("how.flow_3")}</li>
        <li>{t("how.flow_4")}</li>
        <li>{t("how.flow_5")}</li>
      </ol>
      <h2>{t("how.numbers_title")}</h2>
      <p>{t("how.numbers")}</p>
      <h2>{t("how.ai_title")}</h2>
      <p>{t("how.ai")}</p>
    </article>
  );
}
