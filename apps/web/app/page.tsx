import { LandingClient } from "@/components/LandingClient";
import { LandingPick } from "@/components/LandingPick";
import { Photo } from "@/components/Photo";
import { content } from "@/lib/content";
import { t } from "@/lib/t";

// Static. Paints without the API. The question, the two photographs and one button are all that
// sit above the fold on a phone; everything else is below it. The strings and the photographs are
// rendered here on the server and handed down, so the client bundle stays small.
export default function Home() {
  const [left, right] = content.warmup;
  return (
    <div className="landing-hero stack">
      <section className="landing-top">
        <h1>{t("landing.hook")}</h1>
        <LandingPick
          pairLabel={t("landing.pair_label")}
          guessKept={t("landing.guess_kept")}
          cta={t("landing.cta")}
          sides={[
            { id: left.id, photo: <Photo id={left.photo_id} priority first />, pickLabel: t("landing.pick_left") },
            { id: right.id, photo: <Photo id={right.photo_id} priority />, pickLabel: t("landing.pick_right") },
          ]}
        />
      </section>
      <p className="muted small">{t("landing.no_camera")}</p>
      <p>{t("landing.first_line")}</p>
      <p className="small muted">{t("app.one_sentence")}</p>
      <LandingClient />
    </div>
  );
}
