"use client";

import { useSyncExternalStore } from "react";
import { DemoFlow } from "@/components/DemoFlow";
import { FocusHeading } from "@/components/FocusHeading";
import { useQueryParam } from "@/components/QueryParam";
import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { isBeforeLock } from "@/lib/lock";
import { t } from "@/lib/t";

/**
 * Judge mode gives feedback on the same sixteen photos the study uses, so while the study is
 * running it would hand out the answer key. It stays shut until the data lock and loads no photo
 * before then. The server snapshot is "shut", so the static page ships closed and only opens if
 * the browser's own clock has passed the lock.
 */
export default function DemoPage() {
  const scripted = useQueryParam("script") === "1";
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
