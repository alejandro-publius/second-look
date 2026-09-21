"use client";

import { useState } from "react";
import { Sheet } from "./ui/Sheet";
import { t } from "@/lib/t";

/** The longest part of the term the wording actually uses, so the dotted word is one the reader sees. */
export function findTerm(text: string | undefined, term: string): { at: number; word: string } | null {
  if (!text || !term) return null;
  const lower = text.toLowerCase();
  const parts = [term, ...term.split(/[\s-]+/).filter((w) => w.length > 3).sort((a, b) => b.length - a.length)];
  for (const word of parts) {
    const at = lower.indexOf(word.toLowerCase());
    if (at >= 0) return { at, word: text.slice(at, at + word.length) };
  }
  return null;
}

/**
 * The one technical word in a question carries a dotted underline and opens a bottom sheet with a
 * single plain sentence. This renders inside the heading, so when the wording does not contain the
 * word it renders the wording alone and the caller shows GlossaryAside underneath instead.
 */
export function Glossary({ text, term, definition }: { text: string; term: string; definition: string }) {
  const [open, setOpen] = useState(false);
  const found = findTerm(text, term);
  if (!found) return <>{text}</>;
  return (
    <>
      {text.slice(0, found.at)}
      <button type="button" className="glossary-btn glossary-inline" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)}>
        {found.word}
      </button>
      {text.slice(found.at + found.word.length)}
      {open ? (
        <Sheet title={t("glossary.button", { term })} onClose={() => setOpen(false)}>
          <p>{definition}</p>
        </Sheet>
      ) : null}
    </>
  );
}

/** The quiet fallback: a small question under the heading, never at heading size. */
export function GlossaryAside({ term, definition }: { term: string; definition: string }) {
  const [open, setOpen] = useState(false);
  return (
    <p className="small">
      <button type="button" className="glossary-btn" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)}>
        {t("glossary.button", { term })}
      </button>
      {open ? (
        <Sheet title={t("glossary.button", { term })} onClose={() => setOpen(false)}>
          <p>{definition}</p>
        </Sheet>
      ) : null}
    </p>
  );
}
