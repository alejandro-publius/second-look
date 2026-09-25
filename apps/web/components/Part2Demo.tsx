"use client";

import { useMemo, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { Part2Items, type Part2Handlers } from "./Part2Items";
import { Button, ButtonLink } from "./ui/Button";
import { api, type TestAnswer } from "@/lib/api";
import { content } from "@/lib/content";
import { shuffle } from "@/lib/session";
import { t } from "@/lib/t";

/**
 * Judge mode for part 2: the eight photos as the assisted arm meets them, with feedback after
 * every answer through /api/t2/demo. The checker's question appears exactly when it would in the
 * study. Nothing is stored.
 */
export function Part2Demo() {
  const order = useMemo(() => shuffle(content.part2_items.map((i) => i.id)), []);
  const [stage, setStage] = useState<"intro" | "items" | "done">("intro");
  const [right, setRight] = useState(0);

  const handlers: Part2Handlers = {
    async first(itemId, answer: TestAnswer) {
      return (await api.part2Demo(itemId, answer)).ask;
    },
    async choose() {
      // Nothing to store in judge mode. The final answer comes to feedback below.
    },
    async feedback(itemId, finalAnswer) {
      if (finalAnswer === null) return null;
      try {
        const { correct } = await api.part2Demo(itemId, finalAnswer);
        if (correct) setRight((n) => n + 1);
        return { text: correct ? t("demo.feedback_correct") : t("demo.feedback_wrong"), tone: correct ? "ok" : "warn" };
      } catch {
        return { text: t("demo.feedback_unavailable"), tone: "warn" };
      }
    },
  };

  if (stage === "intro") {
    return (
      <div className="stack">
        <FocusHeading>{t("part2.demo_title")}</FocusHeading>
        <p>{t("part2.demo_intro")}</p>
        <div className="actions">
          <Button block onClick={() => setStage("items")}>
            {t("demo.start")}
          </Button>
        </div>
      </div>
    );
  }
  if (stage === "items") return <Part2Items order={order} handlers={handlers} onDone={() => setStage("done")} />;
  return (
    <div className="stack">
      <FocusHeading>{t("demo.done_title")}</FocusHeading>
      <p className="lead">{t("end.total", { correct: right, total: order.length })}</p>
      <p>{t("demo.nothing_stored")}</p>
      <div className="actions">
        <ButtonLink href="/judges" block kind="secondary">
          {t("judges.title")}
        </ButtonLink>
      </div>
    </div>
  );
}
