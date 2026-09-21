"use client";

/* eslint-disable @next/next/no-img-element */
// A plain <img>: the images are our own static files and next/image would add inline styles the
// strict style-src policy blocks.
import { useState } from "react";
import { Button } from "./Button";
import { Icon } from "./Icon";
import { Sheet } from "./Sheet";
import { photoById } from "@/lib/content";
import { t } from "@/lib/t";

export interface Mark {
  x: number;
  y: number;
  label: string;
}

/**
 * A photograph at one radius, with an optional numbered mark layer. Marks come from the lesson
 * YAML as x and y fractions plus a label of five words or fewer, so Rachel places them without
 * code. They stay hidden until asked for, and the same marks are listed in words underneath, so a
 * screen reader gets what a sighted reader gets from the dots.
 */
export function PhotoFrame({
  id,
  large = false,
  priority = false,
  marks = [],
  caption,
  enlargeable = false,
  defaultShowMarks = false,
}: {
  id: string;
  large?: boolean;
  priority?: boolean;
  marks?: Mark[];
  caption?: React.ReactNode;
  enlargeable?: boolean;
  /** The practice photo marks the cue as soon as the answer is given, without a second tap. */
  defaultShowMarks?: boolean;
}) {
  const [shown, setShown] = useState(defaultShowMarks);
  const [big, setBig] = useState(false);
  const p = photoById(id);
  if (!p) return <div className="photo" role="img" aria-label={t("photo.missing", { id })} />;

  const hasMarks = marks.length > 0;
  const alt = shown && hasMarks ? t("photo.alt_with_marks", { alt: p.alt, marks: marks.map((m, i) => `${i + 1}. ${m.label}`).join(". ") }) : p.alt;

  return (
    <figure className="photoframe">
      <span className="photoframe-stage">
        <img className={large ? "photo photo-large" : "photo"} src={p.url} alt={alt} width={p.width} height={p.height} loading={priority ? "eager" : "lazy"} decoding="async" draggable={false} />
        {shown && hasMarks ? (
          // An SVG overlay, because x and y are attributes here. An inline style would be blocked
          // by the style-src policy. The viewBox matches the 4 by 3 frame, so the dots stay round.
          <svg className="photoframe-marks" viewBox="0 0 400 300" aria-hidden="true" focusable="false">
            {marks.map((m, i) => (
              <g key={m.label}>
                <circle className="mark-dot" cx={Math.round(m.x * 400)} cy={Math.round(m.y * 300)} r="15" />
                <text className="mark-num" x={Math.round(m.x * 400)} y={Math.round(m.y * 300)} textAnchor="middle" dominantBaseline="central">
                  {i + 1}
                </text>
              </g>
            ))}
          </svg>
        ) : null}
      </span>
      {caption ? <figcaption>{caption}</figcaption> : null}
      {hasMarks || enlargeable ? (
        <span className="photoframe-tools">
          {hasMarks ? (
            <Button kind="secondary" aria-expanded={shown} onClick={() => setShown((s) => !s)}>
              {shown ? t("photo.hide_marks") : t("photo.show_marks")}
            </Button>
          ) : null}
          {enlargeable ? (
            <Button kind="secondary" onClick={() => setBig(true)}>
              <Icon name="magnifying-glass-plus" />
              {t("photo.enlarge")}
            </Button>
          ) : null}
        </span>
      ) : null}
      {shown && hasMarks ? (
        <ol className="mark-list">
          {marks.map((m, i) => (
            <li key={m.label}>
              <span className="n tabular">{i + 1}</span>
              <span>{m.label}</span>
            </li>
          ))}
        </ol>
      ) : null}
      {big ? (
        <Sheet title={t("photo.enlarged")} onClose={() => setBig(false)}>
          <img className="photo" src={p.url} alt={p.alt} width={p.width} height={p.height} decoding="async" />
        </Sheet>
      ) : null}
    </figure>
  );
}
