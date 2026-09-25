import type { CheckResultOut } from "@/lib/api";
import { has, t } from "@/lib/t";

/** A check's title from the locale. The rule id is a code name and is never shown. */
function checkTitle(ruleId: string): string {
  const key = `spot.rule_${ruleId}`;
  return has(key) ? t(key) : t("spot.rule_other");
}

/** A stored rating (good, moderate, poor) as the word a person reads. */
export function ratingWord(value: string | null): string | null {
  if (!value) return null;
  const key = `spot.rating_word_${value}`;
  return has(key) ? t(key) : value;
}

// The follow-up answers the API accepts, each written as a sentence.
const OUTCOME_KEYS = new Map([
  ["yes", "spot.outcome_yes"],
  ["no", "spot.outcome_no"],
  ["cant_tell", "spot.outcome_cant_tell"],
  ["skipped", "spot.outcome_skipped"],
]);
// The rating check answers. The servers store "change" and always refused "changed", which the
// check page sent until 2026-09-23; "changed" stays here only so an old mock record reads right.
const RATING_ANSWERS = new Set(["keep", "change", "changed"]);

/** The two ratings a check's outcome reads: the first one given and the one the record keeps. */
export interface Ratings {
  first_rating: string | null;
  final_rating: string | null;
}

/** What the person did with a check, in words. The rating check reads the two ratings. */
export function checkOutcome(c: CheckResultOut, v: Ratings): string {
  if (!c.asked) return t("spot.check_not_asked");
  const answer = c.answer ?? null;
  if (!answer) return t("spot.outcome_none");
  if (RATING_ANSWERS.has(answer)) {
    const from = ratingWord(v.first_rating);
    const to = ratingWord(v.final_rating);
    if (from && to && v.first_rating !== v.final_rating) return t("spot.outcome_changed", { from, to });
    const kept = to ?? from;
    if (answer === "keep" || (from && to)) return kept ? t("spot.outcome_kept", { rating: kept }) : t("spot.outcome_kept_plain");
    return t("spot.outcome_changed_plain");
  }
  const said = OUTCOME_KEYS.get(answer);
  if (said) return t(said);
  // A photo follow-up stores the upload id, which means nothing to a person.
  if (c.rule_id === "low_score" || c.detail?.kind === "photo") return t("spot.outcome_photo");
  return t("spot.check_answer", { answer });
}

/**
 * "Checks that ran": each follow-up rule that ran, its question as the person read it, and what
 * they did with it. /spot shows it under a creek check's visit, and a video walk's record, on the
 * phone and as the store keeps it, shows it the same way (judge walk W01). Nothing when no rule ran.
 */
export function ChecksThatRan({ checks, ratings, level = "h3" }: { checks: CheckResultOut[]; ratings: Ratings; level?: "h2" | "h3" }) {
  if (checks.length === 0) return null;
  const Heading = level;
  return (
    <div className="stack" data-testid="checks-ran">
      <Heading>{t("spot.checks")}</Heading>
      <ul className="stack">
        {checks.map((c) => (
          <li key={c.rule_id} className="small">
            <strong>{checkTitle(c.rule_id)}</strong>
            {c.asked && c.question_text ? (
              <>
                <br />
                <span className="muted">{c.question_text}</span>
              </>
            ) : null}
            <br />
            {checkOutcome(c, ratings)}
          </li>
        ))}
      </ul>
    </div>
  );
}
