// The answers a creek check holds, in words, for a record made on the phone (CRITIC_04 F01). /spot
// gets each answer already worded by the API (apps/api/check.py and worker/src/check.ts); a walk's
// record, made on the phone or read back from the walk store as coded answers, is worded here from
// the same form, the same labels and the same yes and no words.
import type { AnswerValue } from "./api";
import { content, type FormItem } from "./content";
import { t } from "./t";

// The yes and no answers in the words /spot gives them (YESNO_LABEL_KEYS in apps/api/check.py).
const YESNO: Record<string, string> = { present: "test.yes", absent: "test.no", cant_tell: "test.cant_tell" };

/** A plant from the region lists by its Latin name, as the question showed it: "common (Latin)". */
function plantLabel(latin: string): string | null {
  for (const region of Object.values(content.regions)) {
    const p = (region.invasive_plants ?? []).find((x) => x.latin_name === latin);
    if (p) return `${p.common_name} (${p.latin_name})`;
  }
  return null;
}

/** One slider as FormQuestion sends it, "joy:3" or "fear:not_applicable", in words. */
function sliderLabel(entry: string): string {
  const [name, v] = entry.split(":");
  const said = v === "not_applicable" || v === "na" ? t("check.slider_na") : v;
  return `${t(`check.slider.${name}`)}: ${said}`;
}

/** One answer in words, from the form's own labels. */
export function answerLabel(item: FormItem, value: AnswerValue): string {
  if (item.type === "sliders") {
    const entries = Array.isArray(value) ? value.map(String) : typeof value === "object" && value !== null ? Object.entries(value).map(([k, v]) => `${k}:${v}`) : [String(value)];
    return entries.map(sliderLabel).join(", ");
  }
  if (item.type === "number") return item.unit ? `${String(value)} ${item.unit}` : String(value);
  const values = Array.isArray(value) ? value : [value];
  return values
    .map((raw) => {
      const v = String(raw);
      if (item.type === "yesno" && v in YESNO) return t(YESNO[v]);
      if (item.type === "pick_region_list") return v === "cant_tell" ? t("check.not_sure") : plantLabel(v) ?? v;
      const option = (item.options ?? []).find((o) => o.value === v);
      return option ? option.label : v.replace(/_/g, " ");
    })
    .join(", ");
}

export interface AnswerRow {
  item_id: string;
  text: string;
  label: string;
  feature: string | null;
}

/** The answers in the form's order, each with its question and its answer in words. A skipped
 * question is not listed, and neither is a list with nothing ticked in it. */
export function answerRows(answers: Record<string, AnswerValue>): AnswerRow[] {
  const given = (value: AnswerValue | undefined) => value !== undefined && !(Array.isArray(value) && value.length === 0);
  return content.form.items
    .filter((item) => given(answers[item.id]))
    .map((item) => ({ item_id: item.id, text: item.text, label: answerLabel(item, answers[item.id]), feature: item.feature }));
}
