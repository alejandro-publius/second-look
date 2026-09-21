"use client";

import { useId, useState } from "react";
import { t } from "@/lib/t";

/** A tap-to-open plain definition. Keyboard reachable, announced through aria-expanded. */
export function Glossary({ term, definition }: { term: string; definition: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div>
      <button type="button" className="glossary-btn" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        {t("glossary.button", { term })}
      </button>
      {open ? (
        <span id={id} className="glossary-note" role="note">
          {definition}
        </span>
      ) : null}
    </div>
  );
}
