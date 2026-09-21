import type { Metadata } from "next";
import { FocusHeading } from "@/components/FocusHeading";
import { Row } from "@/components/ui/Row";
import { shownPhotos } from "@/lib/content";
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
              value={p.license}
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
    </div>
  );
}
