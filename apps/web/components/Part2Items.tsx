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
import { content, featureById, glossaryFor } from "@/lib/content";
import { t } from "@/lib/t";

const itemById = (id: string) => content.part2_items.find((i) => i.id === id);

export interface Part2Handlers {
  /** The first answer. Resolves to whether the checker's question appears. */
  first: (itemId: string, answer: TestAnswer, tFirstMs: number, position: number) => Promise<boolean>;
  /** Keep or Change after the question. changedTo is the person's new pick. */
  choose: (itemId: string, choice: "keep" | "change", changedTo: TestAnswer | undefined, tFinalMs: number) => Promise<void>;
  /** Judge mode only: a line to show once the item is settled. */
  feedback?: (itemId: string, finalAnswer: TestAnswer | null) => Promise<{ text: string; tone: "ok" | "warn" } | null>;
}

/**
 * The eight photos of part 2, one question each, Yes / No / Can't tell and Next, as in part 1.
 * After Next the server says whether the checker's question appears. It never says which way the
 * checker leans. Keep stores the first answer; Change opens the three answers again and the pick
 * is stored. startPending resumes an item whose question was showing when the page reloaded.
 */
export function Part2Items({
  order,
  handlers,
  onDone,
  startIndex = 0,
  startPending = false,
}: {
  order: string[];
  handlers: Part2Handlers;
  onDone: () => void;
  startIndex?: number;
  startPending?: boolean;
}) {
  const [index, setIndex] = useState(startIndex);
  const itemId = order[index];
  if (!itemId) return null;
  const last = index + 1 >= order.length;
  return (
    <div className="stack">
      <Gauge value={index + 1} total={order.length} countText={t("test.progress", { n: index + 1, total: order.length })} live />
      <ItemScreen
        key={itemId}
        itemId={itemId}
        position={index}
        handlers={handlers}
        pending={startPending && index === startIndex}
        last={last}
        onAdvance={() => (last ? onDone() : setIndex(index + 1))}
      />
    </div>
  );
}

type Phase = "answer" | "question" | "change" | "feedback";

function ItemScreen({
  itemId,
  position,
  handlers,
  pending,
  last,
  onAdvance,
}: {
  itemId: string;
  position: number;
  handlers: Part2Handlers;
  pending: boolean;
  last: boolean;
  onAdvance: () => void;
}) {
  const [phase, setPhase] = useState<Phase>(pending ? "question" : "answer");
  const [selected, setSelected] = useState<TestAnswer | null>(null);
  const [first, setFirst] = useState<TestAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [note, setNote] = useState<{ text: string; tone: "ok" | "warn" } | null>(null);
  const shownAt = useRef(0);
  const tFirst = useRef(0);

  useEffect(() => {
    shownAt.current = performance.now();
  }, []);

  const item = itemById(itemId);
  const feature = item ? featureById(item.feature) : undefined;
  if (!item || !feature) {
    return (
      <div className="notice notice-bad" role="alert">
        <Icon name="warning-circle" />
        <p>{t("error.content")}</p>
      </div>
    );
  }

  async function settled(finalAnswer: TestAnswer | null) {
    const fb = handlers.feedback ? await handlers.feedback(itemId, finalAnswer) : null;
    if (fb) {
      setNote(fb);
      setPhase("feedback");
    } else onAdvance();
  }

  async function run(step: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setFailed(false);
    try {
      await step();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  const confirmFirst = () =>
    run(async () => {
      if (selected === null) return;
      tFirst.current = Math.round(performance.now() - shownAt.current);
      const ask = await handlers.first(itemId, selected, tFirst.current, position);
      setFirst(selected);
      if (ask) {
        setPhase("question");
        setSelected(null);
      } else await settled(selected);
    });

  const keep = () =>
    run(async () => {
      await handlers.choose(itemId, "keep", undefined, Math.round(performance.now() - shownAt.current));
      await settled(first);
    });

  const confirmChange = () =>
    run(async () => {
      if (selected === null) return;
      await handlers.choose(itemId, "change", selected, Math.round(performance.now() - shownAt.current));
      await settled(selected);
    });

  const definition = glossaryFor(feature.glossary_term) ?? feature.plain;
  return (
    <div className="stack">
      <PhotoFrame id={item.photo_id} large priority enlargeable />
      <FocusHeading>
        <Glossary text={feature.question} term={feature.glossary_term} definition={definition} />
      </FocusHeading>
      {findTerm(feature.question, feature.glossary_term) ? null : <GlossaryAside term={feature.glossary_term} definition={definition} />}
      {failed ? (
        <div className="notice notice-bad" role="alert">
          <Icon name="warning-circle" />
          <p>{t("error.network")}</p>
        </div>
      ) : null}
      {phase === "answer" ? (
        <AnswerButtons onAnswer={setSelected} selected={selected} disabled={busy} onConfirm={confirmFirst} />
      ) : null}
      {phase === "question" ? (
        <div className="stack" data-testid="part2-question">
          <div className="notice notice-warn" role="status">
            <Icon name="info" />
            <p>{t("part2.question")}</p>
          </div>
          <div className="btn-row">
            <Button onClick={keep} disabled={busy} data-choice="keep">
              {t("part2.keep")}
            </Button>
            <Button kind="secondary" onClick={() => setPhase("change")} disabled={busy} data-choice="change">
              {t("part2.change")}
            </Button>
          </div>
        </div>
      ) : null}
      {phase === "change" ? (
        <div className="stack">
          <p>{t("part2.change_hint")}</p>
          <AnswerButtons onAnswer={setSelected} selected={selected} disabled={busy} onConfirm={confirmChange} />
        </div>
      ) : null}
      {phase === "feedback" && note ? (
        <div className="stack">
          <div className={note.tone === "ok" ? "notice notice-ok" : "notice notice-warn"} role="status">
            <Icon name={note.tone === "ok" ? "check-circle" : "warning"} />
            <p>{note.text}</p>
          </div>
          <div className="actions">
            <Button block onClick={onAdvance}>
              {last ? t("lesson.finish") : t("lesson.next")}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

