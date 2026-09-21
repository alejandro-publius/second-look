"use client";

import { CityView } from "@/components/CityView";
import { useQueryParam } from "@/components/QueryParam";

// /city?creek=<creek id>. A query route, because a static export cannot know a creek id at
// build time. The analyst's door, linked from /judges and never from the participant's page.
export default function CityPage() {
  const creek = useQueryParam("creek");
  return <CityView creekId={creek} />;
}
