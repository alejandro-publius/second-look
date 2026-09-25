"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "./ui/Button";
import { api } from "@/lib/api";
import { t } from "@/lib/t";

/**
 * The one line part 1's score screen gains (UPDATE_31, logged in docs/deviations.md): the offer
 * of part 2. Start goes to /t2, which randomizes; No thanks records the decline and ends. The
 * panel's completion code stays where part 1 shows it, so a person who declines still has it.
 */
export function Part2Offer({ sessionId, onDecline }: { sessionId: string; onDecline: () => void }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  async function decline() {
    setBusy(true);
    // A decline that fails to send is still a decline: the person leaves either way.
    await api.part2Offer(sessionId, "decline").catch(() => undefined);
    onDecline();
  }
  return (
    <section className="card stack" data-testid="part2-offer">
      <h2>{t("part2.title")}</h2>
      <p>{t("part2.offer")}</p>
      <div className="btn-row">
        <Button onClick={() => router.push("/t2")} disabled={busy}>
          {t("part2.offer_start")}
        </Button>
        <Button kind="secondary" onClick={() => void decline()} disabled={busy}>
          {t("part2.offer_skip")}
        </Button>
      </div>
    </section>
  );
}
