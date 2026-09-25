import type { Metadata } from "next";
import Link from "next/link";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("offline.title")}: ${t("app.name")}` };

export default function OfflinePage() {
  return (
    <div className="stack">
      <h1>{t("offline.title")}</h1>
      <p>{t("offline.body")}</p>
      {/* The pages the service worker keeps (offline-budget.mjs OFFLINE_PAGES), in words (critic round 14 W08). */}
      <p>{t("offline.opens")}</p>
      <p>
        <Link href="/check" className="btn">
          {t("nav.check")}
        </Link>
      </p>
    </div>
  );
}
