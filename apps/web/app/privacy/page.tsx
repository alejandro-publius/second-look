import type { Metadata } from "next";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("privacy.title")}: ${t("app.name")}` };

export default function PrivacyPage() {
  return (
    <article className="stack">
      <h1>{t("privacy.title")}</h1>
      <p>{t("privacy.intro")}</p>
      <h2>{t("privacy.stored_title")}</h2>
      <ul>
        <li>{t("privacy.stored_test")}</li>
        <li>{t("privacy.stored_part2")}</li>
        <li>{t("privacy.stored_check")}</li>
        <li>{t("privacy.stored_photos")}</li>
        <li>{t("privacy.stored_walk")}</li>
        <li>{t("privacy.stored_phone")}</li>
      </ul>
      <p>{t("privacy.windows")}</p>
      <h2>{t("privacy.not_stored_title")}</h2>
      <ul>
        <li>{t("privacy.not_stored_1")}</li>
        <li>{t("privacy.not_stored_2")}</li>
        <li>{t("privacy.not_stored_3")}</li>
      </ul>
      <h2>{t("privacy.hosts_title")}</h2>
      <p>{t("privacy.hosts_body")}</p>
      <h2>{t("privacy.rights_title")}</h2>
      <p>{t("privacy.rights_body")}</p>
      <p className="small muted">{t("consent.contact")}</p>
    </article>
  );
}
