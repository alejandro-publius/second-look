"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { AnswerButtons } from "./AnswerButtons";
import { FocusHeading } from "./FocusHeading";
import { findTerm, Glossary, GlossaryAside } from "./Glossary";
import { Button, ButtonLink } from "./ui/Button";
import { Gauge } from "./ui/Gauge";
import { Icon } from "./ui/Icon";
import { PhotoFrame } from "./ui/PhotoFrame";
import type { TestAnswer } from "@/lib/api";
import { featureById, glossaryFor, photoById, testItemById } from "@/lib/content";
import { t } from "@/lib/t";

const KEYBOARD_QUERY = "(hover: hover) and (pointer: fine)";

export interface ItemAnswerResult {
  feedback?: string;
  tone?: "ok" | "warn";
}

/** How the person got to the confirmed answer. Description only; the answer is what is scored. */
export interface AnswerTrail {
  first_choice: TestAnswer;
  t_first_ms: number;
  n_changes: number;
}

type OnAnswer = (itemId: string, answer: TestAnswer, rtMs: number, position: number, trail: AnswerTrail) => Promise<ItemAnswerResult | void> | void;

/**
 * The 16 photos, one question each, Yes / No / Can't tell. In the study no feedback is shown and
 * the flow moves on at once. In judge mode onAnswer returns feedback to show before moving on.
 */
export function TestItems({ order, onAnswer, onDone, withFeedback = false, startIndex = 0 }: { order: string[]; onAnswer: OnAnswer; onDone: () => void; withFeedback?: boolean; startIndex?: number; titleKey?: string }) {
  const [index, setIndex] = useState(startIndex);
  const itemId = order[index];
  if (!itemId) return <Nothing />;
  const last = index + 1 >= order.length;
  return (
    <div className="stack">
      {/* The gauge sits outside the keyed screen below, so the live region is the same node from
          item to item and a screen reader actually hears the count change. */}
      <Gauge value={index + 1} total={order.length} countText={t("test.progress", { n: index + 1, total: order.length })} live />
      <ItemScreen
        key={itemId}
        itemId={itemId}
        nextItemId={order[index + 1]}
        position={index + 1}
        withFeedback={withFeedback}
        onAnswer={onAnswer}
        last={last}
        onAdvance={() => (last ? onDone() : setIndex(index + 1))}
      />
    </div>
  );
}

/** Nothing to show: say what happened and offer the way back, never a blank page. */
export function Nothing() {
  return (
    <div className="stack">
      <div className="notice notice-warn" role="status">
        <Icon name="info" />
        <p>{t("error.nothing_here")}</p>
      </div>
      <div className="actions">
        <ButtonLink href="/" block kind="secondary">
          {t("error.start_over")}
        </ButtonLink>
      </div>
    </div>
  );
}

function ItemScreen({
  itemId,
  nextItemId,
  position,
  withFeedback,
  onAnswer,
  last,
  onAdvance,
}: {
  itemId: string;
  nextItemId?: string;
  position: number;
  withFeedback: boolean;
  onAnswer: OnAnswer;
  last: boolean;
  onAdvance: () => void;
}) {
  const [busy, setBusy] = useState(false);
  // Only tell a person about Y, N and C if they have a keyboard to press them on.
  const keyboard = useSyncExternalStore(
    (notify) => {
      const m = window.matchMedia(KEYBOARD_QUERY);
      m.addEventListener("change", notify);
      return () => m.removeEventListener("change", notify);
    },
    () => window.matchMedia(KEYBOARD_QUERY).matches,
    () => false,
  );
  const [feedback, setFeedback] = useState<ItemAnswerResult | null>(null);
  // Select then Next. Nothing here is on a clock, so a mis-tap can be changed until Next.
  const [selected, setSelected] = useState<TestAnswer | null>(null);
  const shownAt = useRef(0);
  const answered = useRef(false);
  const firstChoice = useRef<TestAnswer | null>(null);
  const tFirst = useRef(0);
  const changes = useRef(0);

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
      if (answered.current) return;
      if (e.key === "Enter") {
        const next = document.querySelector<HTMLButtonElement>("[data-confirm]");
        if (next && !next.disabled && document.activeElement?.getAttribute("data-confirm") === null) {
          e.preventDefault();
          next.click();
        }
        return;
      }
      const map: Record<string, TestAnswer> = { y: "yes", n: "no", c: "cant_tell" };
      const a = map[e.key.toLowerCase()];
      if (!a) return;
      e.preventDefault();
      document.querySelector<HTMLButtonElement>(`[data-answer="${a}"]`)?.click();
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

  /** A tap selects. Nothing is sent and nothing is locked until Next. */
  function choose(a: TestAnswer) {
    if (busy || answered.current) return;
    if (firstChoice.current === null) {
      firstChoice.current = a;
      tFirst.current = Math.round(performance.now() - shownAt.current);
    } else if (a !== selected) {
      changes.current += 1;
    }
    setSelected(a);
  }

  async function confirm() {
    if (busy || answered.current || selected === null) return;
    const rt = Math.round(performance.now() - shownAt.current);
    answered.current = true;
    setBusy(true);
    try {
      const result = await onAnswer(itemId, selected, rt, position, {
        first_choice: firstChoice.current ?? selected,
        t_first_ms: tFirst.current,
        n_changes: changes.current,
      });
      if (withFeedback && result && result.feedback) {
        setFeedback(result);
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
          <AnswerButtons onAnswer={choose} selected={selected} disabled={busy} onConfirm={confirm} />
          {keyboard ? <p className="small muted">{t("test.keys_hint")}</p> : null}
        </>
      )}
    </div>
  );
}
