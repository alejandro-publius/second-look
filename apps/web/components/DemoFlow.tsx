"use client";

import { useMemo, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { Lesson } from "./Lesson";
import { TestItems, type ItemAnswerResult } from "./TestItems";
import { api, type TestAnswer } from "@/lib/api";
import { content, featureById, FEATURE_IDS, type FeatureId } from "@/lib/content";
import { shuffle } from "@/lib/session";
import { t } from "@/lib/t";

const PASS_MIN = 3;

type Stage = { name: "intro" } | { name: "test" } | { name: "result" } | { name: "lesson" } | { name: "done" };

/**
 * Judge mode. Same screens as the test, feedback after every answer through /api/demo/answer,
 * nothing stored, and only the lessons for the features the judge missed. ?script=1 fixes the order.
 */
export function DemoFlow({ scripted }: { scripted: boolean }) {
  const order = useMemo(() => {
    const ids = content.test_items.map((i) => i.id);
    return scripted ? shuffle(ids, "second-look-demo-script") : shuffle(ids);
  }, [scripted]);
  const [stage, setStage] = useState<Stage>({ name: "intro" });
  const [correctBy, setCorrectBy] = useState<Record<string, number>>({});
  const [failures, setFailures] = useState(0);

  async function onAnswer(itemId: string, answer: TestAnswer): Promise<ItemAnswerResult> {
    const item = content.test_items.find((i) => i.id === itemId);
    try {
      const res = await api.demoAnswer(itemId, answer);
      if (res.correct && item) setCorrectBy((m) => ({ ...m, [item.feature]: (m[item.feature] ?? 0) + 1 }));
      return { feedback: res.correct ? t("demo.feedback_correct") : t("demo.feedback_wrong"), tone: res.correct ? "ok" : "warn" };
    } catch {
      setFailures((n) => n + 1);
      return { feedback: t("demo.feedback_unavailable"), tone: "warn" };
    }
  }

  const missed: FeatureId[] = FEATURE_IDS.filter((f) => (correctBy[f] ?? 0) < PASS_MIN);

  switch (stage.name) {
    case "intro":
      return (
        <div className="stack">
          <FocusHeading>{t("demo.title")}</FocusHeading>
          <p>{t("demo.intro")}</p>
          {scripted ? <p className="badge badge-warn">{t("demo.script_note")}</p> : null}
          <button type="button" className="btn btn-block" onClick={() => setStage({ name: "test" })}>
            {t("demo.start")}
          </button>
        </div>
      );
    case "test":
      return <TestItems order={order} onAnswer={onAnswer} onDone={() => setStage({ name: "result" })} withFeedback titleKey="demo.title" />;
    case "result":
      return (
        <div className="stack">
          <FocusHeading>{t("demo.result_title")}</FocusHeading>
          {failures > 0 ? <p className="notice notice-warn">{t("demo.feedback_unavailable")}</p> : null}
          <ul>
            {FEATURE_IDS.map((f) => (
              <li key={f}>{t("end.per_feature", { correct: correctBy[f] ?? 0, total: 4, feature: featureById(f)?.name ?? f })}</li>
            ))}
          </ul>
          {missed.length === 0 ? (
            <p className="notice notice-ok">{t("demo.missed_none")}</p>
          ) : (
            <>
              <p>{t("demo.missed_intro")}</p>
              <ul>
                {missed.map((f) => (
                  <li key={f}>{featureById(f)?.name}</li>
                ))}
              </ul>
              <button type="button" className="btn btn-block" onClick={() => setStage({ name: "lesson" })}>
                {t("demo.lesson_start")}
              </button>
            </>
          )}
          <p className="small muted">{t("demo.nothing_stored")}</p>
        </div>
      );
    case "lesson":
      return <Lesson features={missed} onDone={() => setStage({ name: "done" })} titleKey="demo.lesson_title" />;
    case "done":
      return (
        <div className="stack">
          <FocusHeading>{t("demo.done_title")}</FocusHeading>
          <p>{t("demo.nothing_stored")}</p>
          <p>{t("end.last_line")}</p>
        </div>
      );
  }
}
