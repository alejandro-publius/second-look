"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

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
  pickLabel: string;
}

export function LandingPick({ sides, thisOne, guessKept, cta, pairLabel }: { sides: [PickSide, PickSide]; thisOne: string; guessKept: string; cta: string; pairLabel: string }) {
  const [picked, setPicked] = useState<string | null>(null);
  const [href, setHref] = useState("/t");

  useEffect(() => {
    const src = new URLSearchParams(window.location.search).get("src");
    if (src) setHref(`/t?src=${encodeURIComponent(src)}`);
  }, []);

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
          <button key={s.id} type="button" className="landing-pick" aria-pressed={picked === s.id} onClick={() => pick(s.id)} aria-label={s.pickLabel}>
            {s.photo}
            <span className="pick-label">{thisOne}</span>
          </button>
        ))}
      </div>
      {picked ? (
        <p className="landing-answer small muted" role="status">
          {guessKept}
        </p>
      ) : null}
      <Link href={href} className="btn btn-block" id="cta">
        {cta}
      </Link>
    </>
  );
}
