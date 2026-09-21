"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { captureSource } from "@/lib/session";

/** Runs after first paint: keeps the ?src= label and wakes the API. Renders nothing. */
export function LandingClient() {
  useEffect(() => {
    captureSource(window.location.search);
    const id = window.setTimeout(() => {
      void api.health();
    }, 50);
    return () => window.clearTimeout(id);
  }, []);
  return null;
}
