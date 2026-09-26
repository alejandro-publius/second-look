"use client";

import { PhotoPicker, type PickedPhoto } from "./PhotoPicker";
import type { Followup } from "@/lib/api";
import { has, t } from "@/lib/t";

/** A follow-up's plain name, as "Checks that ran" titles it (spot.rule_*). The rule id is a code
 *  name, so a screen reader must never announce it (critic round 14 B04, round 15 F06). */
function ruleTitle(ruleId: string): string {
  const key = `spot.rule_${ruleId}`;
  return has(key) ? t(key) : t("spot.rule_other");
}

/** A stored rating (good, moderate, poor) as the word a person reads. */
function ratingWord(value: string | null): string {
  const key = `spot.rating_word_${value ?? ""}`;
  return has(key) ? t(key) : (value ?? "");
}

/** What the rating follow-up holds: its answer, the rating the record will carry, and whether the picker is open. */
export interface RatingFollowup {
  answer: string | undefined;
  finalRating: string | null;
  changingRating: boolean;
}

/** A tap on the rating follow-up: Keep, Change, or a rating picked after Change. */
export type RatingTap = "keep" | "change" | { rating: string };

/**
 * The rating follow-up after one tap. Keep puts the first rating back and closes the picker, so a
 * record can never say keep beside a changed rating. Change opens the picker, and a rating picked
 * there becomes the final one.
 */
export function tapRating(
  state: RatingFollowup,
  tap: RatingTap,
  firstRating: string | null,
): RatingFollowup {
  if (tap === "keep")
    return { answer: "keep", finalRating: firstRating, changingRating: false };
  if (tap === "change") return { ...state, changingRating: true };
  return { answer: "change", finalRating: tap.rating, changingRating: false };
}

/**
 * One follow-up question and its answers, in place. The creek check shows the ones the API picked
 * after Send; a video walk shows the ones the same rules pick from its answers (judge walk W01).
 */
export function FollowupCard({
  followup,
  value,
  onAnswer,
  photos,
  onPhotos,
  changingRating,
  ratingOptions,
  finalRating,
  onRatingTap,
}: {
  followup: Followup;
  value: string | undefined;
  onAnswer: (v: string) => void;
  photos: PickedPhoto[];
  onPhotos: (p: PickedPhoto[]) => void;
  changingRating: boolean;
  ratingOptions: {
    id: string;
    label: string;
    value: string;
    description?: string;
  }[];
  finalRating: string | null;
  onRatingTap: (tap: RatingTap) => void;
}) {
  return (
    <section
      className="card stack"
      aria-label={ruleTitle(followup.rule_id)}
      data-rule={followup.rule_id}
    >
      <p>
        <strong>{followup.question_text}</strong>
      </p>
      {followup.kind === "yesno" ? (
        <div className="option-list">
          {[
            ["yes", t("check.yes")],
            ["no", t("check.no")],
            ["cant_tell", t("check.not_sure")],
          ].map(([v, label]) => (
            <button
              key={v}
              type="button"
              className="option"
              aria-pressed={value === v}
              onClick={() => onAnswer(v)}
            >
              {label}
            </button>
          ))}
        </div>
      ) : null}
      {/* Keep and Change look the same until one is pressed, and the pressed one is marked as a
          pick, as an option is. Once a rating is settled, the card says which one the record keeps,
          so a tap never seems to do nothing (critic round 14 B02, round 15 F03). */}
      {followup.kind === "keep_rating" ? (
        <div className="stack">
          <div className="btn-row">
            <button
              type="button"
              className="btn btn-secondary"
              aria-pressed={value === "keep"}
              onClick={() => onRatingTap("keep")}
            >
              {t("check.keep_rating")}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              aria-pressed={value === "change" || changingRating}
              onClick={() => onRatingTap("change")}
            >
              {t("check.change_rating")}
            </button>
          </div>
          {changingRating ? (
            <div className="option-list">
              {ratingOptions.map((o) => (
                <button
                  key={o.id}
                  type="button"
                  className="option"
                  aria-pressed={finalRating === o.value}
                  onClick={() => onRatingTap({ rating: o.value })}
                >
                  {o.label}
                  {o.description ? (
                    <span className="small muted option-description">
                      {" "}
                      {o.description}
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          ) : null}
          <p className="small" role="status" data-testid="rating-chosen">
            {!changingRating && finalRating && value === "keep"
              ? t("check.rating_kept", { rating: ratingWord(finalRating) })
              : !changingRating && finalRating && value === "change"
                ? t("check.rating_new", { rating: ratingWord(finalRating) })
                : ""}
          </p>
        </div>
      ) : null}
      {followup.kind === "look_again" ? (
        <div className="btn-row">
          <button
            type="button"
            className="btn btn-secondary"
            aria-pressed={value === "looked"}
            onClick={() => onAnswer("looked")}
          >
            {t("check.looked_again")}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            aria-pressed={value === "skipped"}
            onClick={() => onAnswer("skipped")}
          >
            {t("check.skip")}
          </button>
        </div>
      ) : null}
      {followup.kind === "photo" ? (
        <div className="stack">
          <PhotoPicker photos={photos} onChange={onPhotos} max={1} />
          <button
            type="button"
            className="btn btn-quiet"
            aria-pressed={value === "skipped"}
            onClick={() => onAnswer("skipped")}
          >
            {t("check.skip")}
          </button>
        </div>
      ) : null}
    </section>
  );
}
