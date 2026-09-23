"use client";

import { CityView } from "@/components/CityView";
import { useQueryParam } from "@/components/QueryParam";
import { WalkCity } from "@/components/WalkCity";

// /city?creek=<creek id>. A query route, because a static export cannot know a creek id at
// build time. The analyst's door, linked from /judges and never from the participant's page.
export default function CityPage() {
  const creek = useQueryParam("creek");
  const walk = useQueryParam("walk");
  // /city?walk=<id> is the demo creek a video walk feeds, built on this phone only.
  if (walk) return <WalkCity walkId={walk} />;
  return <CityView creekId={creek} />;
}
