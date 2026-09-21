"use client";

import { useEffect } from "react";
import { startQueueWatcher } from "@/lib/offline";

/** Sends checks that were saved on this phone once the network is back. Renders nothing. */
export function QueueWatcher() {
  useEffect(() => startQueueWatcher(), []);
  return null;
}
