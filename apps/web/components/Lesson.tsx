"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChoiceList } from "./ui/ChoiceList";
import { FocusHeading } from "./FocusHeading";
import { Button } from "./ui/Button";
import { Gauge } from "./ui/Gauge";
import { Icon } from "./ui/Icon";
import { PhotoFrame } from "./ui/PhotoFrame";
import { Nothing } from "./TestItems";
import type { TestAnswer } from "@/lib/api";
import { featureById, lessonFor, type ContrastPair, type FeatureId, type Lesson as LessonContent } from "@/lib/content";
import { t } from "@/lib/t";

type Screen = { id: string; feature: FeatureId; kind: "rule" | "pair2" | "practice" };

/**
 * The lesson card. The photograph leads, the rule of thumb is the heading, and the marks on the
 * photo are revealed on a tap so the person looks before being told. Seconds per screen go to
 * onDone.
 */
export function Lesson({ features, onDone }: { features: FeatureId[]; onDone: (seconds: Record<string, number>) => void; titleKey?: string }) {
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
  if (!screen) return <Nothing />;
  const feature = featureById(screen.feature);
  const lesson = lessonFor(screen.feature);
  if (!feature || !lesson) return <Nothing />;

  function next() {
    const s = screens[index];
    const elapsed = (performance.now() - shownAt.current) / 1000;
    seconds.current[s.id] = Math.round(((seconds.current[s.id] ?? 0) + elapsed) * 10) / 10;
    if (index + 1 >= screens.length) onDone({ ...seconds.current });
    else setIndex(index + 1);
  }

  const last = index + 1 >= screens.length;
  const featureNo = features.indexOf(screen.feature) + 1;

  return (
    <div className="stack" key={screen.id}>
      {index > 0 ? (
        <p className="small">
          <button type="button" className="btn btn-quiet" onClick={() => setIndex(index - 1)}>
            <Icon name="caret-left" size={20} />
            {t("nav.back")}
          </button>
        </p>
      ) : null}
      {/* The count says which job the gauge is doing here: how far through the lesson, not a score. */}
      <Gauge value={featureNo} total={features.length} countText={t("gauge.lesson_count", { feature: feature.name, value: featureNo, total: features.length })} live />
      {/* The rule of thumb is the heading of the card, not a callout underneath it. */}
      <FocusHeading>{lesson.rule_of_thumb}</FocusHeading>
      {!lesson.approved ? (
        <div className="notice notice-warn">
          <Icon name="warning" />
          <p>{t("lesson.draft_badge")}</p>
        </div>
      ) : null}
      {screen.kind === "practice" ? (
        <PracticeScreen lesson={lesson} question={feature.question} onNext={next} last={last} />
      ) : (
        <>
          <Pair pair={screen.kind === "pair2" ? lesson.contrast_pairs[1] : lesson.contrast_pairs[0]} />
          <div className="actions">
            <Button block onClick={next}>
              {t("lesson.next")}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

/** What people assume, beside what is actually there. The marks sit on the second photo. */
function Pair({ pair }: { pair: ContrastPair | undefined }) {
  if (!pair) return null;
  return (
    <div className="pair lesson-pair">
      <PhotoFrame
        id={pair.assume_photo_id}
        priority
        caption={
          <>
            <strong>{t("lesson.assume")}</strong>
            <br />
            {pair.assume_caption}
          </>
        }
      />
      <PhotoFrame
        id={pair.actual_photo_id}
        priority
        marks={pair.marks ?? []}
        caption={
          <>
            <strong>{t("lesson.actual")}</strong>
            <br />
            {pair.actual_caption}
          </>
        }
      />
    </div>
  );
}

/** One practice photo. The feedback names the cue and marks where it is, with no extra tap. */
function PracticeScreen({ lesson, question, onNext, last }: { lesson: LessonContent; question: string; onNext: () => void; last: boolean }) {
  const [answer, setAnswer] = useState<TestAnswer | null>(null);
  const correct = answer !== null && ((answer === "yes" && lesson.practice.gold === "present") || (answer === "no" && lesson.practice.gold === "absent"));
  return (
    <>
      <p className="muted small">{t("lesson.practice_intro")}</p>
      <PhotoFrame key={answer === null ? "clean" : "marked"} id={lesson.practice.photo_id} large priority marks={answer === null ? [] : (lesson.practice_marks ?? [])} defaultShowMarks={answer !== null} />
      <h2>{question}</h2>
      {answer === null ? (
        <div className="actions">
          <ChoiceList<TestAnswer>
            groupLabel={t("test.answer_group")}
            onChoose={setAnswer}
            choices={[
              { value: "yes", label: t("test.yes") },
              { value: "no", label: t("test.no") },
              { value: "cant_tell", label: t("test.cant_tell") },
            ]}
          />
        </div>
      ) : (
        <div className="stack">
          <div className={correct ? "notice notice-ok" : "notice notice-warn"} role="status">
            <Icon name={correct ? "check-circle" : "warning"} />
            <p>
              <strong>{correct ? t("lesson.practice_right") : t("lesson.practice_wrong")}</strong> {correct ? lesson.practice.feedback_correct : lesson.practice.feedback_wrong}
            </p>
          </div>
          <div className="actions">
            <Button block onClick={onNext}>
              {last ? t("lesson.finish") : t("lesson.next")}
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
