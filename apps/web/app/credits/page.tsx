import type { Metadata } from "next";
import { FocusHeading } from "@/components/FocusHeading";
import { Row } from "@/components/ui/Row";
import { content, licenseUrl, shownPhotos, type InatChecks } from "@/lib/content";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("credits.title")}: ${t("app.name")}` };

const INAT_TERMS = "https://www.inaturalist.org/pages/terms";

/** What iNaturalist said about one of its photos when scripts/verify_inat_photos.py asked. */
function inatVerdict(c: InatChecks["photos"][string]): string {
  if (!c.found) return t("credits.inat_not_found");
  if (c.research_grade && c.in_california) return t("credits.inat_ok");
  const said: string[] = [];
  if (!c.research_grade) said.push(t("credits.inat_not_research"));
  if (!c.in_california) said.push(t("credits.inat_not_california"));
  return said.join(" ");
}

function checkedOn(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-US", { dateStyle: "medium", timeZone: "UTC" });
}

// CC BY and CC BY-SA ask us to name the author wherever the photograph appears. One page that
// lists every photograph a visitor can see is the honest way to do that, and the build refuses
// to run if a photograph that needs an author does not have one.
export default function CreditsPage() {
  const photos = shownPhotos();
  const real = photos.filter((p) => !p.placeholder);
  const placeholders = photos.length - real.length;
  // The open footage in the video: named here too, with the video's own licence (UPDATE_22 6.6).
  const video = content.video_credits;
  // The photos iNaturalist was asked about, with its answer beside each (UPDATE_29 section 8).
  const inat = content.inat_checks ?? { checked_at: "", photos: {} };
  const inatCount = real.filter((p) => inat.photos[p.id]).length;
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
                <>
                  {licenseUrl(p.license) ? (
                    <a href={licenseUrl(p.license)} rel="license noreferrer">
                      {p.license}
                    </a>
                  ) : (
                    p.license
                  )}
                  {inat.photos[p.id] ? <>. {inatVerdict(inat.photos[p.id])}</> : null}
                </>
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
      <section className="stack" aria-labelledby="inat-credits">
        <h2 id="inat-credits">{t("credits.inat_title")}</h2>
        {inatCount > 0 ? <p>{t("credits.inat_intro", { n: inatCount, date: checkedOn(inat.checked_at) })}</p> : null}
        <p>{t("credits.inat_context")}</p>
        <p>
          <a href={INAT_TERMS} rel="noreferrer">
            {t("credits.inat_terms")}
          </a>
        </p>
      </section>
      {(content.footage_credits ?? []).length > 0 ? (
        <section className="stack">
          <h2>{t("credits.footage_title")}</h2>
          <p>{t("credits.footage_intro")}</p>
          {/* A title is long and goes in the value, which wraps; the end slot never shrinks, and a
              title there made this page 713 pixels wide on a phone (REVIEW_03 R26). */}
          <div className="card">
            {content.footage_credits.map((v) => (
              <Row
                key={v.id}
                label={t("credits.by", { author: v.author })}
                value={
                  <>
                    <a href={v.source_url} rel="noreferrer nofollow">
                      {v.title}
                    </a>
                    <br />
                    {licenseUrl(v.license) ? (
                      <a href={licenseUrl(v.license)} rel="license noreferrer">
                        {v.license}
                      </a>
                    ) : (
                      v.license
                    )}
                  </>
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
                  <>
                    <a href={v.source_url} rel="noreferrer nofollow">
                      {v.title}
                    </a>
                    <br />
                    <a href={v.license_url} rel="license noreferrer">
                      {v.license}
                    </a>
                  </>
                }
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
