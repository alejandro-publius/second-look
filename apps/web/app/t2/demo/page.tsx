"use client";

import { useSyncExternalStore } from "react";
import { FocusHeading } from "@/components/FocusHeading";
import { Part2Demo } from "@/components/Part2Demo";
import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { isJudgeModeShut } from "@/lib/lock";
import { t } from "@/lib/t";

/**
 * Judge mode for part 2. Like /demo it gives feedback on photos the study uses, so it is shut
 * until the second lock (UPDATE_33; lib/lock.ts, JUDGE_MODE_OPENS_UTC) and loads no photo before
 * then. Like /demo it has three states: the page as built is "unknown" and shows the heading
 * alone, and the browser's own clock then says "shut" or "open" (audit finding time-bombs-5). The
 * answer route refuses before the second lock on the server's clock, whatever the browser says.
 */
export default function Part2DemoPage() {
  const state = useSyncExternalStore<"unknown" | "shut" | "open">(
    () => () => undefined,
    () => (isJudgeModeShut() ? "shut" : "open"),
    () => "unknown",
  );
  if (state === "unknown") {
    return (
      <div className="stack">
        <FocusHeading>{t("part2.demo_title")}</FocusHeading>
      </div>
    );
  }
  if (state === "shut") {
    return (
      <div className="stack">
        <FocusHeading>{t("demo.shut_title")}</FocusHeading>
        <div className="notice notice-warn">
          <Icon name="info" />
          <p>{t("part2.demo_shut_body")}</p>
        </div>
        <p>{t("demo.shut_meanwhile")}</p>
        <div className="actions">
          <ButtonLink href="/judges" block kind="secondary">
            {t("judges.title")}
          </ButtonLink>
        </div>
      </div>
    );
  }
  return <Part2Demo />;
}
