"use client";

import { useState, useSyncExternalStore } from "react";
import { ButtonLink } from "./ui/Button";

/**
 * The opening question. The two photographs are the control, not decoration: tapping one is the
 * person's guess. It is kept in this browser and becomes the warm-up answer only after consent.
 * This reveal is the one orchestrated moment in the product.
 *
 * Everything it needs arrives as props, and the photographs arrive already rendered by the server,
 * so the landing page's client bundle never pulls in the whole content file.
 */
export interface PickSide {
  id: string;
  photo: React.ReactNode;
  /** The visible label. It also has to be the accessible name, so speech control can say it. */
  pickLabel: string;
}

export function LandingPick({ sides, guessKept, cta, pairLabel }: { sides: [PickSide, PickSide]; guessKept: string; cta: string; pairLabel: string }) {
  const [picked, setPicked] = useState<string | null>(null);
  const src = useSyncExternalStore(
    () => () => undefined,
    () => new URLSearchParams(window.location.search).get("src") ?? "",
    () => "",
  );
  const href = src ? `/t?src=${encodeURIComponent(src)}` : "/t";

  function pick(id: string) {
    setPicked(id);
    try {
      sessionStorage.setItem("sl_landing_guess", id);
    } catch {
      // storage blocked: the warm-up screen asks the question instead
    }
  }

  return (
    <>
      <div className="pair" role="group" aria-label={pairLabel}>
        {sides.map((s) => (
          <button key={s.id} type="button" className="landing-pick" aria-pressed={picked === s.id} onClick={() => pick(s.id)}>
            {s.photo}
            <span className="pick-label">{s.pickLabel}</span>
          </button>
        ))}
      </div>
      <p className="landing-answer small muted" role="status">
        {picked ? guessKept : null}
      </p>
      <ButtonLink href={href} block>
        {cta}
      </ButtonLink>
    </>
  );
}
