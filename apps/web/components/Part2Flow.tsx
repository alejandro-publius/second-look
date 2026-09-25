"use client";

import { useCallback, useEffect, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { Part2Items, type Part2Handlers } from "./Part2Items";
import { Button, ButtonLink } from "./ui/Button";
import { Icon } from "./ui/Icon";
import { Skeleton } from "./ui/Skeleton";
import { api, ApiError, type Part2AnswerRequest, type Part2ChoiceRequest, type Part2State } from "@/lib/api";
import { PANEL_COMPLETION_CODE, usePanel } from "@/lib/panel";
import { getOpenPart2, setOpenPart2 } from "@/lib/part2";
import { getOpenSession } from "@/lib/session";
import { t } from "@/lib/t";

type Stage =
  | { name: "restoring" }
  | { name: "not_yet" }
  | { name: "intro"; state: Part2State }
  | { name: "items"; state: Part2State; startIndex: number; pending: boolean }
  | { name: "completing" }
  | { name: "score"; correct: number; total: number }
  | { name: "error"; retry: "restore" | "complete"; state?: Part2State };

/** What this page sent, kept so the end can send again whatever the server says it lacks. */
interface Book {
  answers: Map<string, Part2AnswerRequest>;
  choices: Map<string, Part2ChoiceRequest>;
  settled: Set<string>;
}

/** Where to pick up: the item whose question was showing, else the first one not yet answered. */
function resumePoint(state: Part2State): { startIndex: number; pending: boolean } {
  if (state.pending) return { startIndex: Math.max(0, state.item_order.indexOf(state.pending)), pending: true };
  const done = new Set(state.answered);
  const next = state.item_order.findIndex((id) => !done.has(id));
  return { startIndex: next < 0 ? state.item_order.length : next, pending: false };
}

function handlersFor(part2_id: string, book: Book): Part2Handlers {
  return {
    async first(item_id, answer, t_first_ms, position) {
      const body = { part2_id, item_id, answer, t_first_ms, position };
      book.answers.set(item_id, body);
      const { ask } = await api.part2Answer(body);
      if (!ask) book.settled.add(item_id);
      return ask;
    },
    async choose(item_id, choice, changed_to, t_final_ms) {
      const body: Part2ChoiceRequest = { part2_id, item_id, choice, changed_to, t_final_ms };
      book.choices.set(item_id, body);
      await api.part2Choice(body);
      book.settled.add(item_id);
    },
  };
}

/**
 * Part 2, the assisted second look (UPDATE_31). Reached only from part 1's score screen: the
 * server refuses a start for a sitting that has not reached it, and this page then says so. The
 * server randomizes, keeps the flags and says after each first answer whether to ask.
 */
export function Part2Flow() {
  const [stage, setStage] = useState<Stage>({ name: "restoring" });
  const [attempt, setAttempt] = useState(0);
  const [book] = useState<Book>(() => ({ answers: new Map(), choices: new Map(), settled: new Set() }));
  const panel = usePanel();

  useEffect(() => {
    let live = true;
    const go = (next: Stage) => {
      if (live) setStage(next);
    };
    const begin = (state: Part2State) => {
      setOpenPart2({ part2_id: state.part2_id, session_id: getOpenSession()?.session_id ?? "" });
      for (const id of state.answered) book.settled.add(id);
      if (state.completed) return go({ name: "score", correct: state.correct_total ?? 0, total: state.total });
      if (state.answered.length === 0 && !state.pending) return go({ name: "intro", state });
      go({ name: "items", state, ...resumePoint(state) });
    };
    (async () => {
      const part1 = getOpenSession();
      const open = getOpenPart2();
      try {
        if (open && (!part1 || open.session_id === part1.session_id || open.session_id === "")) {
          return begin(await api.part2Resume(open.part2_id));
        }
        if (!part1) return go({ name: "not_yet" });
        const offered = await api.part2Offer(part1.session_id, "start");
        if ("declined" in offered) return go({ name: "not_yet" });
        begin(offered);
      } catch (err) {
        if (err instanceof ApiError && (err.status === 404 || err.status === 409)) return go({ name: "not_yet" });
        go({ name: "error", retry: "restore" });
      }
    })();
    return () => {
      live = false;
    };
  }, [attempt, book]);

  const complete = useCallback(
    async (state: Part2State) => {
      setStage({ name: "completing" });
      try {
        let done = await api.part2Complete(state.part2_id, book.settled.size);
        if (done.need_resend) {
          // Send again what the server says it lacks, the answer first and then the choice.
          for (const id of done.need_resend) {
            const a = book.answers.get(id);
            const c = book.choices.get(id);
            if (a) await api.part2Answer(a).catch(() => undefined);
            if (c) await api.part2Choice(c).catch(() => undefined);
          }
          done = await api.part2Complete(state.part2_id, book.settled.size, true);
        }
        setStage({ name: "score", correct: done.correct_total ?? 0, total: done.total ?? state.item_order.length });
      } catch {
        setStage({ name: "error", retry: "complete", state });
      }
    },
    [book],
  );

  switch (stage.name) {
    case "restoring":
    case "completing":
      return <Skeleton label={t("end.scoring")} lines={3} photo={false} />;
    case "not_yet":
      return (
        <div className="stack">
          <FocusHeading>{t("part2.not_yet_title")}</FocusHeading>
          <p>{t("part2.not_yet")}</p>
          <div className="actions">
            <ButtonLink href="/t" block>
              {t("part2.to_test")}
            </ButtonLink>
          </div>
        </div>
      );
    case "intro":
      return (
        <div className="stack">
          <FocusHeading>{t("part2.title")}</FocusHeading>
          <p>{t("part2.intro")}</p>
          <div className="actions">
            <Button block onClick={() => setStage({ name: "items", state: stage.state, startIndex: 0, pending: false })}>
              {t("part2.start")}
            </Button>
          </div>
        </div>
      );
    case "items":
      return (
        <Part2Items
          order={stage.state.item_order}
          handlers={handlersFor(stage.state.part2_id, book)}
          startIndex={stage.startIndex}
          startPending={stage.pending}
          onDone={() => void complete(stage.state)}
        />
      );
    case "score":
      return (
        <div className="stack">
          <FocusHeading>{t("part2.score_title")}</FocusHeading>
          <p className="lead" data-testid="part2-score">
            {t("end.total", { correct: stage.correct, total: stage.total })}
          </p>
          {panel ? (
            <p className="notice notice-ok" data-testid="panel-code">
              {t("end.panel_code", { code: PANEL_COMPLETION_CODE })}
            </p>
          ) : null}
          <p>{t("end.done")}</p>
          <p>{t("end.last_line")}</p>
        </div>
      );
    case "error":
      return (
        <div className="stack">
          <div className="notice notice-bad" role="alert">
            <Icon name="warning-circle" />
            <p>{t("error.network")}</p>
          </div>
          <div className="actions">
            <Button
              block
              onClick={() => {
                if (stage.retry === "complete" && stage.state) void complete(stage.state);
                else {
                  setStage({ name: "restoring" });
                  setAttempt((n) => n + 1);
                }
              }}
            >
              {t("error.retry")}
            </Button>
          </div>
        </div>
      );
  }
}
