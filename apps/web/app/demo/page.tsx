"use client";

import { useSyncExternalStore } from "react";
import { DemoFlow } from "@/components/DemoFlow";
import { FocusHeading } from "@/components/FocusHeading";
import { useQueryParam } from "@/components/QueryParam";
import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { isJudgeModeShut } from "@/lib/lock";
import { t } from "@/lib/t";

/**
 * Judge mode gives feedback on the same sixteen photos the study uses, so while the study is
 * running it would hand out the answer key. It is shut until the second lock, the end of the
 * study's second wave (UPDATE_33; lib/lock.ts, JUDGE_MODE_OPENS_UTC), and loads no photo before
 * then.
 *
 * Three states. A static page cannot know the time, so the page as built is "unknown": the
 * heading alone, with no notice, no photo and no button. It used to be built shut, so after the
 * lock every reader saw the shut page, "Judge mode opens on ...", until the script had run, and
 * for good with scripts off (audit finding time-bombs-5). The browser's own clock then says "shut"
 * or "open". A browser whose clock is before the second lock still gets the shut page, and the
 * answer route refuses before it on the server's clock, whatever the browser says.
 */
export default function DemoPage() {
  const scripted = useQueryParam("script") === "1";
  const state = useSyncExternalStore<"unknown" | "shut" | "open">(
    () => () => undefined,
    () => (isJudgeModeShut() ? "shut" : "open"),
    () => "unknown",
  );
  if (state === "unknown") {
    return (
      <div className="stack">
        <FocusHeading>{t("demo.title")}</FocusHeading>
      </div>
    );
  }
  if (state === "shut") {
    return (
      <div className="stack">
        <FocusHeading>{t("demo.shut_title")}</FocusHeading>
        <div className="notice notice-warn">
          <Icon name="info" />
          <p>{t("demo.shut_body")}</p>
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
  return <DemoFlow scripted={scripted} />;
}
