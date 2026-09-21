"use client";

import { SpotRecord } from "@/components/SpotRecord";
import { useQueryParam } from "@/components/QueryParam";

// /spot?id=<spot id>. A query route, not a path route, because Cloudflare Pages serves a static
// export and a spot id is not known at build time.
export default function SpotPage() {
  const id = useQueryParam("id");
  return <SpotRecord spotId={id} />;
}
