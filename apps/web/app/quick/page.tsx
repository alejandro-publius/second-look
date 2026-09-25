"use client";

import Link from "next/link";
import { FocusHeading } from "@/components/FocusHeading";
import { QueueWatcher } from "@/components/QueueWatcher";
import { QuickCheck } from "@/components/QuickCheck";
import { useQueryParamOrNull } from "@/components/QueryParam";
import { t } from "@/lib/t";

// /quick?spot=<spot id>. A query route for the same reason as /spot. The quick check adds to a
// spot that has a record, so with no spot in the link it could never be sent: the API has no route
// for an empty spot, and Send would end on "try again", which can never work. With no spot the
// page says where the quick check opens from, and links the full check instead (CRITIC_09 R04).
export default function QuickPage() {
  const spot = useQueryParamOrNull("spot");
  if (spot === null) {
    return (
      <p role="status" className="muted">
        {t("spot.loading")}
      </p>
    );
  }
  return (
    <>
      {spot === "" ? (
        <div className="stack">
          <FocusHeading>{t("quick.title")}</FocusHeading>
          <p className="notice notice-warn">{t("quick.no_spot")}</p>
          <p>
            <Link className="btn btn-block" href="/check">
              {t("quick.no_spot_link")}
            </Link>
          </p>
        </div>
      ) : (
        <QuickCheck spotId={spot} />
      )}
      <QueueWatcher />
    </>
  );
}
