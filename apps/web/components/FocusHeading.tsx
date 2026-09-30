"use client";

import { useEffect, useRef } from "react";

/** A heading that takes focus when it appears, so keyboard and screen reader users follow each screen. */
export function FocusHeading({
  children,
  level = 1,
  id,
}: {
  children: React.ReactNode;
  level?: 1 | 2;
  /** For a section's aria-labelledby, as a plain heading would carry it. */
  id?: string;
}) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    ref.current?.focus({ preventScroll: false });
  }, []);
  if (level === 2) {
    return (
      <h2 ref={ref} tabIndex={-1} id={id}>
        {children}
      </h2>
    );
  }
  return (
    <h1 ref={ref} tabIndex={-1} id={id}>
      {children}
    </h1>
  );
}
