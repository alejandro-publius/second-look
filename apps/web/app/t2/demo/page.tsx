"use client";

import { useSyncExternalStore } from "react";
import { FocusHeading } from "@/components/FocusHeading";
import { Part2Demo } from "@/components/Part2Demo";
import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { isBeforeLock } from "@/lib/lock";
import { t } from "@/lib/t";

/**
 * Judge mode for part 2. Like /demo it gives feedback on photos the study uses, so it stays shut
 * until the data lock and loads no photo before then. The server snapshot is "shut".
 */
export default function Part2DemoPage() {
  const shut = useSyncExternalStore(
    () => () => undefined,
    () => isBeforeLock(),
    () => true,
  );
  if (shut) {
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
