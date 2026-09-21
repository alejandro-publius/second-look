import type { Metadata } from "next";
import Link from "next/link";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("about.title")}: ${t("app.name")}` };

export default function AboutPage() {
  return (
    <article className="stack">
      <h1>{t("about.title")}</h1>
      <p>{t("app.one_sentence")}</p>
      <p>{t("about.p1")}</p>
      <p>{t("about.p2")}</p>
      <p>{t("about.p3")}</p>
      <p>{t("about.licence")}</p>
      <p>
        <Link href="/t" className="btn">
          {t("landing.cta")}
        </Link>
      </p>
      <nav className="site-footer" aria-label={t("nav.more")}>
        <Link href="/privacy">{t("nav.privacy")}</Link> <Link href="/how-we-know">{t("nav.how_we_know")}</Link>
      </nav>
    </article>
  );
}
