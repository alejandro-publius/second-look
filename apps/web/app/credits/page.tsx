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
  // The open footage in the video: named here too, with the video's own licence (UPDATE_22 6.6).
  const video = content.video_credits;
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
                value={
                  licenseUrl(v.license) ? (
                    <a href={licenseUrl(v.license)} rel="license noreferrer">
                      {v.license}
                    </a>
                  ) : (
                    v.license
                  )
                }
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
      {(video?.items ?? []).length > 0 ? (
        <section className="stack">
          <h2>{t("credits.video_title")}</h2>
          <p>{t("credits.video_intro")}</p>
          <p>
            <a href={video.licence_url} rel="license noreferrer">
              {t("credits.video_licence", { licence: video.licence })}
            </a>
          </p>
          <div className="card">
            {video.items.map((v) => (
              <Row
                key={v.title}
                label={t("credits.by", { author: v.author })}
                value={
                  <a href={v.license_url} rel="license noreferrer">
                    {v.license}
                  </a>
                }
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
