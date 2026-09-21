"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnswerButtons } from "./AnswerButtons";
import { FocusHeading } from "./FocusHeading";
import { Photo } from "./Photo";
import { Progress } from "./Progress";
import type { TestAnswer } from "@/lib/api";
import { featureById, lessonFor, type ContrastPair, type FeatureId, type Lesson as LessonContent } from "@/lib/content";
import { t } from "@/lib/t";

type Screen = { id: string; feature: FeatureId; kind: "rule" | "pair2" | "practice" };

/**
 * The lesson: one card per feature, each with the rule of thumb, two contrast pairs and one practice
 * photo with feedback. Seconds per screen are reported to onDone.
 */
export function Lesson({ features, onDone, titleKey = "lesson.title" }: { features: FeatureId[]; onDone: (seconds: Record<string, number>) => void; titleKey?: string }) {
  const screens = useMemo<Screen[]>(() => {
    const out: Screen[] = [];
    for (const f of features) {
      if (!lessonFor(f)) continue;
      out.push({ id: `${f}/rule`, feature: f, kind: "rule" });
      out.push({ id: `${f}/pair2`, feature: f, kind: "pair2" });
      out.push({ id: `${f}/practice`, feature: f, kind: "practice" });
    }
    return out;
  }, [features]);

  const [index, setIndex] = useState(0);
  const seconds = useRef<Record<string, number>>({});
  const shownAt = useRef(0);

  useEffect(() => {
    shownAt.current = performance.now();
  }, [index]);

  const screen = screens[index];
  if (!screen) return null;
  const feature = featureById(screen.feature);
  const lesson = lessonFor(screen.feature);
  if (!feature || !lesson) return null;

  function next() {
    const s = screens[index];
    const elapsed = (performance.now() - shownAt.current) / 1000;
    seconds.current[s.id] = Math.round(((seconds.current[s.id] ?? 0) + elapsed) * 10) / 10;
    if (index + 1 >= screens.length) onDone({ ...seconds.current });
    else setIndex(index + 1);
  }

  const last = index + 1 >= screens.length;

  return (
    <div className="stack" key={screen.id}>
      <Progress value={index + 1} max={screens.length} />
      <FocusHeading>
        {t(titleKey)}: {feature.name}
      </FocusHeading>
      {!lesson.approved ? <span className="badge badge-warn">{t("lesson.draft_badge")}</span> : null}
      {screen.kind === "practice" ? (
        <PracticeScreen lesson={lesson} question={feature.question} onNext={next} last={last} />
      ) : (
        <>
          {screen.kind === "rule" ? (
            <p className="card">
              <strong>{lesson.rule_of_thumb}</strong>
            </p>
          ) : null}
          <Pair pair={screen.kind === "pair2" ? lesson.contrast_pairs[1] : lesson.contrast_pairs[0]} />
          <div className="btn-row">
            <button type="button" className="btn" onClick={next}>
              {t("lesson.next")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function Pair({ pair }: { pair: ContrastPair | undefined }) {
  if (!pair) return null;
  return (
    <div className="pair">
      <figure>
        <Photo id={pair.assume_photo_id} priority />
        <figcaption>
          <strong>{t("lesson.assume")}</strong>
          <br />
          {pair.assume_caption}
        </figcaption>
      </figure>
      <figure>
        <Photo id={pair.actual_photo_id} priority />
        <figcaption>
          <strong>{t("lesson.actual")}</strong>
          <br />
          {pair.actual_caption}
        </figcaption>
      </figure>
    </div>
  );
}

/** One practice photo with feedback that names the cue. Its state lives here, so it resets per screen. */
function PracticeScreen({ lesson, question, onNext, last }: { lesson: LessonContent; question: string; onNext: () => void; last: boolean }) {
  const [answer, setAnswer] = useState<TestAnswer | null>(null);
  const correct = answer !== null && ((answer === "yes" && lesson.practice.gold === "present") || (answer === "no" && lesson.practice.gold === "absent"));
  return (
    <>
      <p className="muted small">{t("lesson.practice_intro")}</p>
      <Photo id={lesson.practice.photo_id} large priority />
      <p>
        <strong>{question}</strong>
      </p>
      {answer === null ? (
        <AnswerButtons onAnswer={setAnswer} />
      ) : (
        <div className="stack">
          <p className={correct ? "notice notice-ok" : "notice notice-warn"} role="status">
            <strong>{correct ? t("lesson.practice_right") : t("lesson.practice_wrong")}</strong> {correct ? lesson.practice.feedback_correct : lesson.practice.feedback_wrong}
          </p>
          <div className="btn-row">
            <button type="button" className="btn" onClick={onNext}>
              {last ? t("lesson.finish") : t("lesson.next")}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
