"use client";

import { CityView } from "@/components/CityView";
import { useQueryParam, useQueryParamOrNull } from "@/components/QueryParam";
import { WalkCity } from "@/components/WalkCity";

// /city?creek=<creek id>. A query route, because a static export cannot know a creek id at
// build time. The analyst's door, linked from /judges and never from the participant's page.
export default function CityPage() {
  // Null until the browser has read the address, so a link that names no creek ("") is told apart
  // from one not read yet, and the page never says to pick a creek to a link that names one.
  const creek = useQueryParamOrNull("creek");
  const walk = useQueryParam("walk");
  const record = useQueryParam("record");
  // /city?walk=<id> is the demo creek a video walk feeds: the walk this browser finished, and the
  // stored walk record the link names with &record=<id>.
  if (walk) return <WalkCity walkId={walk} recordId={record} />;
  return <CityView creekId={creek} />;
}
