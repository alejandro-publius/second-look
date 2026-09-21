import { t } from "@/lib/t";

/**
 * The staff gauge: the striped measuring stick a surveyor stands in a stream. One block per item,
 * square ends, a heavier tick every fifth block, so a count is readable before the numeral is.
 * It is the progress bar in the test and the score mark on a record.
 *
 * The blocks are hidden from assistive technology on purpose: the count beside them already says
 * the same thing in words, and announcing both would read every screen twice.
 */
export function Gauge({
  value,
  total,
  size = "bar",
  hollow = false,
  countText,
  srText,
  live = false,
}: {
  value: number;
  total: number;
  size?: "bar" | "mark";
  hollow?: boolean;
  countText?: string;
  /** Extra context for a screen reader when the visible count does not carry all of it. */
  srText?: string;
  live?: boolean;
}) {
  const safeTotal = Math.max(1, Math.round(total));
  const filled = Math.min(safeTotal, Math.max(0, Math.round(value)));
  const blocks = Array.from({ length: safeTotal }, (_, i) => i);
  const count = countText ?? t("gauge.count", { value: filled, total: safeTotal });
  return (
    <div className={`gauge gauge-${size}${hollow ? " gauge-hollow" : ""}`}>
      <span className="gauge-count tabular" aria-live={live ? "polite" : undefined}>
        {count}
        {srText ? <span className="visually-hidden">. {srText}</span> : null}
      </span>
      <span className="gauge-blocks" aria-hidden="true">
        {blocks.map((i) => (
          <span key={i} className={`gauge-block${i < filled ? " is-full" : ""}${(i + 1) % 5 === 0 && i + 1 !== safeTotal ? " is-fifth" : ""}`} />
        ))}
      </span>
    </div>
  );
}
