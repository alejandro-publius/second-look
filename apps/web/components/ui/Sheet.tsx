"use client";

import { useCallback, useEffect, useRef } from "react";
import { Icon } from "./Icon";
import { t } from "@/lib/t";

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select,textarea,[tabindex]:not([tabindex="-1"])';

/**
 * A bottom sheet: the glossary word, an enlarged photograph and, in stage 2, View as FHIR.
 * Focus is trapped while it is open, Escape closes it, and the trigger gets focus back.
 */
export function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  const panel = useRef<HTMLDivElement>(null);
  const opener = useRef<Element | null>(null);

  useEffect(() => {
    opener.current = document.activeElement;
    const first = panel.current?.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();
    const restore = opener.current;
    return () => {
      if (restore instanceof HTMLElement) restore.focus();
    };
  }, []);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const items = Array.from(panel.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    },
    [onClose],
  );

  return (
    // The scrim is a plain backdrop. Closing is offered by the button and by Escape, so this
    // click handler is a convenience and not the only way out.
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions, jsx-a11y/click-events-have-key-events
    <div className="sheet-scrim" onClick={(e) => e.target === e.currentTarget && onClose()} onKeyDown={onKeyDown}>
      <div className="sheet-panel" ref={panel} role="dialog" aria-modal="true" aria-label={title}>
        <div className="sheet-head">
          <h2>{title}</h2>
          <button type="button" className="sheet-close" onClick={onClose}>
            <Icon name="x" label={t("sheet.close")} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
