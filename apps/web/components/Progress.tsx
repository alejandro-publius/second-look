import { Gauge } from "./ui/Gauge";
import { t } from "@/lib/t";

/** Words plus the staff gauge. The words are the fact; the gauge makes it countable at a glance. */
export function Progress({ value, max, labelKey = "progress.step" }: { value: number; max: number; labelKey?: string }) {
  const label = t(labelKey, { n: value, total: max });
  return <Gauge value={value} total={max} countText={label} live />;
}
