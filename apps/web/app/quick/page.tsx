"use client";

import { QueueWatcher } from "@/components/QueueWatcher";
import { QuickCheck } from "@/components/QuickCheck";
import { useQueryParam } from "@/components/QueryParam";

// /quick?spot=<spot id>. A query route for the same reason as /spot.
export default function QuickPage() {
  const spot = useQueryParam("spot");
  return (
    <>
      <QuickCheck spotId={spot} />
      <QueueWatcher />
    </>
  );
}
