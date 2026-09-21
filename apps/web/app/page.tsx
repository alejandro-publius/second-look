import Link from "next/link";
import { Photo } from "@/components/Photo";
import { LandingClient } from "@/components/LandingClient";
import { content } from "@/lib/content";
import { t } from "@/lib/t";

// Static. Paints without the API. LandingClient wakes the API after paint and keeps ?src=.
export default function Home() {
  const [left, right] = content.warmup;
  return (
    <div className="landing-hero stack">
      <h1>{t("landing.hook")}</h1>
      <div className="pair" aria-label={t("landing.pair_label")} role="group">
        <Photo id={left.photo_id} priority />
        <Photo id={right.photo_id} priority />
      </div>
      <p>
        <Link href="/t" className="btn btn-block" id="cta">
          {t("landing.cta")}
        </Link>
      </p>
      <p className="muted">{t("landing.no_camera")}</p>
      <p>{t("landing.first_line")}</p>
      <p className="small muted">{t("app.one_sentence")}</p>
      <nav className="site-footer" aria-label={t("nav.more")}>
        <Link href="/demo">{t("nav.demo")}</Link> <Link href="/check">{t("nav.check")}</Link>{" "}
        <Link href="/how-we-know">{t("nav.how_we_know")}</Link> <Link href="/two">{t("nav.two")}</Link>
      </nav>
      <LandingClient />
    </div>
  );
}
