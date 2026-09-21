"use client";

import { useEffect, useRef, useState } from "react";
import { AnswerButtons } from "./AnswerButtons";
import { FocusHeading } from "./FocusHeading";
import { Glossary } from "./Glossary";
import { Photo } from "./Photo";
import { Progress } from "./Progress";
import type { TestAnswer } from "@/lib/api";
import { featureById, glossaryFor, testItemById } from "@/lib/content";
import { t } from "@/lib/t";

export interface ItemAnswerResult {
  feedback?: string;
  tone?: "ok" | "warn";
}

type OnAnswer = (itemId: string, answer: TestAnswer, rtMs: number, position: number) => Promise<ItemAnswerResult | void> | void;

/**
 * The 16 photos, one question each, Yes / No / Can't tell. In the study no feedback is shown and
 * the flow moves on at once. In judge mode onAnswer returns feedback to show before moving on.
 */
export function TestItems({ order, onAnswer, onDone, withFeedback = false, titleKey = "test.title" }: { order: string[]; onAnswer: OnAnswer; onDone: () => void; withFeedback?: boolean; titleKey?: string }) {
  const [index, setIndex] = useState(0);
  const itemId = order[index];
  if (!itemId) return null;
  const last = index + 1 >= order.length;
  return (
    <ItemScreen
      key={itemId}
      itemId={itemId}
      position={index + 1}
      total={order.length}
      titleKey={titleKey}
      withFeedback={withFeedback}
      onAnswer={onAnswer}
      last={last}
      onAdvance={() => (last ? onDone() : setIndex(index + 1))}
    />
  );
}

function ItemScreen({
  itemId,
  position,
  total,
  titleKey,
  withFeedback,
  onAnswer,
  last,
  onAdvance,
}: {
  itemId: string;
  position: number;
  total: number;
  titleKey: string;
  withFeedback: boolean;
  onAnswer: OnAnswer;
  last: boolean;
  onAdvance: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<ItemAnswerResult | null>(null);
  const shownAt = useRef(0);

  useEffect(() => {
    shownAt.current = performance.now();
  }, []);

  const item = testItemById(itemId);
  const feature = item ? featureById(item.feature) : undefined;
  if (!item || !feature) {
    return <p className="notice notice-bad">{t("error.content")}</p>;
  }

  async function answer(a: TestAnswer) {
    if (busy) return;
    const rt = Math.round(performance.now() - shownAt.current);
    setBusy(true);
    try {
      const result = await onAnswer(itemId, a, rt, position);
      if (withFeedback && result && result.feedback) setFeedback(result);
      else onAdvance();
    } finally {
      setBusy(false);
    }
  }

  const definition = glossaryFor(feature.glossary_term) ?? feature.plain;

  return (
    <div className="stack">
      <Progress value={position} max={total} labelKey="test.progress" />
      <FocusHeading>{t(titleKey)}</FocusHeading>
      <Photo id={item.photo_id} large priority />
      <p>
        <strong>{feature.question}</strong>
      </p>
      <Glossary term={feature.glossary_term} definition={definition} />
      {feedback ? (
        <div className="stack">
          <p className={feedback.tone === "ok" ? "notice notice-ok" : "notice notice-warn"} role="status">
            {feedback.feedback}
          </p>
          <div className="btn-row">
            <button type="button" className="btn" onClick={onAdvance}>
              {last ? t("lesson.finish") : t("lesson.next")}
            </button>
          </div>
        </div>
      ) : (
        <AnswerButtons onAnswer={answer} disabled={busy} />
      )}
    </div>
  );
}
