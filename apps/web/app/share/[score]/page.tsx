import type { Metadata } from "next";
import Link from "next/link";
import { siteUrl } from "@/lib/session";
import { t } from "@/lib/t";

const TOTAL = 16;

// The link a person shares. Its preview image is the score card. Static for every possible score.
export function generateStaticParams() {
  return Array.from({ length: TOTAL + 1 }, (_, i) => ({ score: String(i) }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ score: string }> }): Promise<Metadata> {
  const { score } = await params;
  const title = t("end.share", { correct: Number(score), total: TOTAL });
  const image = `${siteUrl()}/api/share/${score}`;
  return {
    title: `${title} ${t("app.name")}`,
    description: t("app.one_sentence"),
    openGraph: { title, description: t("landing.no_camera"), images: [{ url: image, width: 1200, height: 630 }] },
    twitter: { card: "summary_large_image", title, images: [image] },
  };
}

export default async function SharePage({ params }: { params: Promise<{ score: string }> }) {
  const { score } = await params;
  const n = Number(score);
  return (
    <div className="stack landing-hero">
      <h1>{t("share.title", { correct: n, total: TOTAL })}</h1>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="share-card" src={`/api/share/${n}`} alt={t("end.share_card_alt", { correct: n, total: TOTAL })} width={1200} height={630} />
      <p>{t("share.beat")}</p>
      <p>
        <Link href="/t?src=friends" className="btn btn-block">
          {t("landing.cta")}
        </Link>
      </p>
      <p className="muted">{t("landing.no_camera")}</p>
    </div>
  );
}
