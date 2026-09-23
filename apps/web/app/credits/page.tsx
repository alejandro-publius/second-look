import type { Metadata } from "next";
import { FocusHeading } from "@/components/FocusHeading";
import { Row } from "@/components/ui/Row";
import { content, licenseUrl, shownPhotos } from "@/lib/content";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("credits.title")}: ${t("app.name")}` };

// CC BY and CC BY-SA ask us to name the author wherever the photograph appears. One page that
// lists every photograph a visitor can see is the honest way to do that, and the build refuses
// to run if a photograph that needs an author does not have one.
export default function CreditsPage() {
  const photos = shownPhotos();
  const real = photos.filter((p) => !p.placeholder);
  const placeholders = photos.length - real.length;
  return (
    <div className="stack">
      <FocusHeading>{t("credits.title")}</FocusHeading>
      <p>{t("credits.intro")}</p>
      {real.length === 0 ? <p className="muted">{t("credits.none")}</p> : null}
      {real.length > 0 ? (
        <div className="card">
          {real.map((p) => (
            <Row
              key={p.id}
              label={p.author ? t("credits.by", { author: p.author }) : p.id}
              value={
                licenseUrl(p.license) ? (
                  <a href={licenseUrl(p.license)} rel="license noreferrer">
                    {p.license}
                  </a>
                ) : (
                  p.license
                )
              }
              end={
                p.source_url ? (
                  <a href={p.source_url} rel="noreferrer nofollow">
                    {t("credits.source")}
                  </a>
                ) : undefined
              }
            />
          ))}
        </div>
      ) : null}
      {placeholders > 0 ? <p className="small muted">{t("credits.placeholder_note")}</p> : null}
      {(content.footage_credits ?? []).length > 0 ? (
        <section className="stack">
          <h2>{t("credits.footage_title")}</h2>
          <p>{t("credits.footage_intro")}</p>
          <div className="card">
            {content.footage_credits.map((v) => (
              <Row
                key={v.id}
                label={t("credits.by", { author: v.author })}
                value={v.license}
                end={
                  <a href={v.source_url} rel="noreferrer nofollow">
                    {v.title}
                  </a>
                }
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
