import { t } from "@/lib/t";

export function Progress({ value, max, labelKey = "progress.step" }: { value: number; max: number; labelKey?: string }) {
  const label = t(labelKey, { n: value, total: max });
  return (
    <div className="stack">
      <p className="small muted" aria-live="polite">
        {label}
      </p>
      <progress value={value} max={max} aria-label={label} />
    </div>
  );
}
