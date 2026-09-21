"use client";

import { FocusHeading } from "./FocusHeading";
import { Photo } from "./Photo";
import { content } from "@/lib/content";
import { t } from "@/lib/t";

/** Two creek photos side by side, one question, no feedback. The choice is recorded as a description. */
export function Warmup({ onChoice }: { onChoice: (warmupId: string) => void }) {
  const [left, right] = content.warmup;
  return (
    <div className="stack">
      <FocusHeading>{t("warmup.question")}</FocusHeading>
      <p className="muted small">{t("warmup.intro")}</p>
      <div className="pair">
        <figure>
          <Photo id={left.photo_id} priority />
          <figcaption>
            <button type="button" className="btn btn-block" onClick={() => onChoice(left.id)} aria-label={t("warmup.pick_left")}>
              {t("warmup.left")}
            </button>
          </figcaption>
        </figure>
        <figure>
          <Photo id={right.photo_id} priority />
          <figcaption>
            <button type="button" className="btn btn-block" onClick={() => onChoice(right.id)} aria-label={t("warmup.pick_right")}>
              {t("warmup.right")}
            </button>
          </figcaption>
        </figure>
      </div>
    </div>
  );
}
