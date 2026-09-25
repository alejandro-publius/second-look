"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FocusHeading } from "@/components/FocusHeading";
import { QueueWatcher } from "@/components/QueueWatcher";
import { QuickCheck } from "@/components/QuickCheck";
import { useQueryParamOrNull } from "@/components/QueryParam";
import { api, ApiError } from "@/lib/api";
import { t } from "@/lib/t";

/** Neutral words while the page reads its link: it loads no record (CRITIC_10 T02). */
function Loading() {
  return (
    <p role="status" className="muted">
      {t("quick.loading")}
    </p>
  );
}

/** Where the quick check opens from, with the full check instead, when there is no spot to add to. */
function NoSpot() {
  return (
    <div className="stack">
      <FocusHeading>{t("quick.title")}</FocusHeading>
      <p className="notice notice-warn">{t("quick.no_spot")}</p>
      <p>
        <Link className="btn btn-block" href="/check">
          {t("quick.no_spot_link")}
        </Link>
      </p>
    </div>
  );
}

/**
 * The form, once the API has said the spot has a record. A spot it does not know gets the no-spot
 * notice, as Send could only fail there (CRITIC_10 T02). Any other failure, such as no network,
 * still shows the form, because a quick check made offline waits on the phone and goes later.
 */
function QuickForSpot({ spotId }: { spotId: string }) {
  const [known, setKnown] = useState<{ spotId: string; ok: boolean } | null>(null);
  useEffect(() => {
    let live = true;
    api
      .spot(spotId)
      .then(() => live && setKnown({ spotId, ok: true }))
      .catch((err) => live && setKnown({ spotId, ok: !(err instanceof ApiError && err.status === 404) }));
    return () => {
      live = false;
    };
  }, [spotId]);
  if (known === null || known.spotId !== spotId) return <Loading />;
  return known.ok ? <QuickCheck spotId={spotId} /> : <NoSpot />;
}

// /quick?spot=<spot id>. A query route for the same reason as /spot. The quick check adds to a
// spot that has a record, so with no spot in the link it could never be sent: the API has no route
// for an empty spot, and Send would end on "try again", which can never work. With no spot the
// page says where the quick check opens from, and links the full check instead (CRITIC_09 R04).
export default function QuickPage() {
  const spot = useQueryParamOrNull("spot");
  if (spot === null) return <Loading />;
  return (
    <>
      {spot === "" ? <NoSpot /> : <QuickForSpot spotId={spot} />}
      <QueueWatcher />
    </>
  );
}
