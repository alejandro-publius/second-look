import type { Metadata } from "next";
import Link from "next/link";
import { t } from "@/lib/t";

// Its own tab title, not the landing page's (critic round 14 P02).
export const metadata: Metadata = { title: `${t("notfound.title")}: ${t("app.name")}` };

// Any address with no page (CRITIC_11 W02). The framework's own page set inline styles, which the
// site's CSP blocks, and gave no way on but the wordmark. This one is in the site's own words and
// classes, with no inline style. The static export writes it as out/404.html, which Cloudflare
// Pages serves for any address with no file.
export default function NotFound() {
  return (
    <div className="stack">
      <h1>{t("notfound.title")}</h1>
      <p>{t("notfound.body")}</p>
      <p>
        <Link href="/" className="btn">
          {t("notfound.home")}
        </Link>
      </p>
      <p>
        <Link href="/judges">{t("notfound.judges")}</Link>
      </p>
    </div>
  );
}
