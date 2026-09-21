"use client";

import { FocusHeading } from "./FocusHeading";
import { Button } from "./ui/Button";
import { PhotoFrame } from "./ui/PhotoFrame";
import { content } from "@/lib/content";
import { t } from "@/lib/t";

/**
 * The fallback warm-up, for someone who reached /t without passing the landing page. Two creek
 * photos, one question, no feedback. The choice is recorded as a description, never scored.
 */
export function Warmup({ onChoice }: { onChoice: (warmupId: string) => void }) {
  const [left, right] = content.warmup;
  return (
    <div className="stack">
      <FocusHeading>{t("warmup.question")}</FocusHeading>
      <p className="muted small">{t("warmup.intro")}</p>
      <div className="pair">
        {[left, right].map((w, i) => (
          <div key={w.id}>
            <PhotoFrame id={w.photo_id} priority />
            <Button block kind="secondary" onClick={() => onChoice(w.id)} aria-label={t(i === 0 ? "warmup.pick_left" : "warmup.pick_right")}>
              {t(i === 0 ? "warmup.left" : "warmup.right")}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
