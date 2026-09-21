import type { Metadata } from "next";
import QRCode from "qrcode";
import { PRINT_INK, PRINT_PAPER } from "../theme";
import { Photo } from "@/components/Photo";
import { content } from "@/lib/content";
import { siteUrl } from "@/lib/session";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("poster.title")}: ${t("app.name")}` };

// The printable poster. The QR code is drawn here at build time with the qrcode package, so nothing
// is fetched from anywhere. It points at the site with ?src=poster. No answer is printed.
export default async function PosterPage() {
  const url = `${siteUrl()}/?src=poster`;
  const svg = await QRCode.toString(url, { type: "svg", errorCorrectionLevel: "M", margin: 1, color: { dark: PRINT_INK, light: PRINT_PAPER } });
  const [left, right] = content.warmup;
  return (
    <div className="poster">
      <h1>{t("landing.hook")}</h1>
      <div className="pair" role="group" aria-label={t("landing.pair_label")}>
        <Photo id={left.photo_id} priority />
        <Photo id={right.photo_id} priority />
      </div>
      <p className="scan">{t("poster.scan")}</p>
      <div className="qr" role="img" aria-label={t("poster.qr_alt")} dangerouslySetInnerHTML={{ __html: svg }} />
      <p className="url">{url}</p>
      <p className="small">{t("app.name")}</p>
    </div>
  );
}
