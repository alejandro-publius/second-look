"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { captureSource } from "@/lib/session";

/** Runs after first paint: keeps the ?src= label for the session and wakes the API. Renders nothing. */
export function LandingClient() {
  useEffect(() => {
    captureSource(window.location.search);
    const cta = document.getElementById("cta") as HTMLAnchorElement | null;
    const src = new URLSearchParams(window.location.search).get("src");
    if (cta && src) cta.href = `/t?src=${encodeURIComponent(src)}`;
    const id = window.setTimeout(() => {
      void api.health();
    }, 50);
    return () => window.clearTimeout(id);
  }, []);
  return null;
}
