"use client";

import { useEffect, useRef, useState } from "react";
import { AnswerButtons } from "./AnswerButtons";
import { FocusHeading } from "./FocusHeading";
import { findTerm, Glossary, GlossaryAside } from "./Glossary";
import { Button } from "./ui/Button";
import { Gauge } from "./ui/Gauge";
import { Icon } from "./ui/Icon";
import { PhotoFrame } from "./ui/PhotoFrame";
import type { TestAnswer } from "@/lib/api";
import { featureById, glossaryFor, photoById, testItemById } from "@/lib/content";
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
export function TestItems({ order, onAnswer, onDone, withFeedback = false }: { order: string[]; onAnswer: OnAnswer; onDone: () => void; withFeedback?: boolean; titleKey?: string }) {
  const [index, setIndex] = useState(0);
  const itemId = order[index];
  if (!itemId) return null;
  const last = index + 1 >= order.length;
  return (
    <ItemScreen
      key={itemId}
      itemId={itemId}
      nextItemId={order[index + 1]}
      position={index + 1}
      total={order.length}
      withFeedback={withFeedback}
      onAnswer={onAnswer}
      last={last}
      onAdvance={() => (last ? onDone() : setIndex(index + 1))}
    />
  );
}

function ItemScreen({
  itemId,
  nextItemId,
  position,
  total,
  withFeedback,
  onAnswer,
  last,
  onAdvance,
}: {
  itemId: string;
  nextItemId?: string;
  position: number;
  total: number;
  withFeedback: boolean;
  onAnswer: OnAnswer;
  last: boolean;
  onAdvance: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<ItemAnswerResult | null>(null);
  const shownAt = useRef(0);
  const answered = useRef(false);

  useEffect(() => {
    shownAt.current = performance.now();
  }, []);

  const item = testItemById(itemId);
  const feature = item ? featureById(item.feature) : undefined;

  // Y, N and C answer on a keyboard. Ignored while a field has focus or a sheet is open.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const el = document.activeElement;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.closest?.("[role='dialog']"))) return;
      const map: Record<string, TestAnswer> = { y: "yes", n: "no", c: "cant_tell" };
      const a = map[e.key.toLowerCase()];
      if (!a || answered.current) return;
      e.preventDefault();
      const btn = document.querySelector<HTMLButtonElement>(`[data-answer="${a}"]`);
      btn?.click();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!item || !feature) {
    return (
      <div className="notice notice-bad" role="alert">
        <Icon name="warning-circle" />
        <p>{t("error.content")}</p>
      </div>
    );
  }

  async function answer(a: TestAnswer) {
    if (busy || answered.current) return;
    const rt = Math.round(performance.now() - shownAt.current);
    answered.current = true;
    setBusy(true);
    try {
      const result = await onAnswer(itemId, a, rt, position);
      if (withFeedback && result && result.feedback) {
        setFeedback(result);
        answered.current = false;
      } else onAdvance();
    } finally {
      setBusy(false);
    }
  }

  const definition = glossaryFor(feature.glossary_term) ?? feature.plain;
  const nextPhoto = nextItemId ? photoById(testItemById(nextItemId)?.photo_id ?? "") : undefined;

  return (
    <div className="stack">
      {/* The next photo is fetched while this one is being answered. */}
      {nextPhoto ? <link rel="preload" as="image" href={nextPhoto.url} /> : null}
      <Gauge value={position} total={total} countText={t("test.progress", { n: position, total })} live />
      <PhotoFrame id={item.photo_id} large priority enlargeable />
      <FocusHeading>
        <Glossary text={feature.question} term={feature.glossary_term} definition={definition} />
      </FocusHeading>
      {findTerm(feature.question, feature.glossary_term) ? null : <GlossaryAside term={feature.glossary_term} definition={definition} />}
      {feedback ? (
        <div className="stack">
          <div className={feedback.tone === "ok" ? "notice notice-ok" : "notice notice-warn"} role="status">
            <Icon name={feedback.tone === "ok" ? "check-circle" : "warning"} />
            <p>{feedback.feedback}</p>
          </div>
          <div className="actions">
            <Button block onClick={onAdvance}>
              {last ? t("lesson.finish") : t("lesson.next")}
            </Button>
          </div>
        </div>
      ) : (
        <>
          <AnswerButtons onAnswer={answer} disabled={busy} />
          <p className="small muted">{t("test.keys_hint")}</p>
        </>
      )}
    </div>
  );
}
