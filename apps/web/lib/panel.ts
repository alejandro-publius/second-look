/**
 * The panel study (the team's working notes (PANEL STUDY), UPDATE_29 section 1). A person who arrives with
 * ?src=panel sees one extra sentence on the consent screen and this code after the score. Nothing
 * else changes. The code is fixed and public on purpose: the panel only checks that a person
 * reached the end, and no panel identifier from the link is ever kept (lib/session.ts strips it).
 */
import { useSyncExternalStore } from "react";
import { sourceLabel } from "./session";

export const PANEL_SOURCE = "panel";
export const PANEL_COMPLETION_CODE = "SLCREEK26";

/** True when this visit came through the panel: from the link, or the label kept for the session. */
export function isPanel(search: string, storedLabel: string): boolean {
  return new URLSearchParams(search).get("src") === PANEL_SOURCE || storedLabel === PANEL_SOURCE;
}

/** Whether this visit came through the panel, read on the client only (false while prerendering). */
export function usePanel(): boolean {
  return useSyncExternalStore(
    () => () => undefined,
    () => isPanel(window.location.search, sourceLabel()),
    () => false,
  );
}
