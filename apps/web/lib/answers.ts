// The answers a creek check holds, in words, for a record made on the phone (CRITIC_04 F01). /spot
// gets each answer already worded by the API (apps/api/check.py and worker/src/check.ts); a walk's
// record, made on the phone or read back from the walk store as coded answers, is worded here from
// the same form, the same labels and the same yes and no words.
//
// A record reads the answers back in the language they were given in (audit finding
// phone-ux-languages-2): the official app's own words for the question and for each answer, and
// English, marked as English, where a translation fell back or the words are our own.
import type { AnswerValue } from "./api";
import { content, type FormItem } from "./content";
import { englishOptions, itemText, optionText, type Shown } from "./lang";
import { t } from "./t";

// The yes and no answers in the words /spot gives them (YESNO_LABEL_KEYS in apps/api/check.py).
const YESNO: Record<string, string> = { present: "test.yes", absent: "test.no", cant_tell: "test.cant_tell" };

/** One piece of an answer in words. `join` stands before it when it is not the first piece. */
export interface AnswerPiece extends Shown {
  join?: string;
}

/** A plant from the region lists by its Latin name, as the question showed it: "common (Latin)". */
function plantLabel(latin: string): string | null {
  for (const region of Object.values(content.regions)) {
    const p = (region.invasive_plants ?? []).find((x) => x.latin_name === latin);
    if (p) return `${p.common_name} (${p.latin_name})`;
  }
  return null;
}

/** Our own English words, which another language shows as English and says so. */
function ours(text: string, lang: string): Shown {
  return { text, lang: "en", english: lang !== "en" };
}

/** An answer of the app's: our record's English in English, the app's own words in another
 * language, and the English the question screen showed where that translation fell back. */
function appWords(item: FormItem, id: string, english: string, lang: string): Shown {
  if (lang === "en") return ours(english, lang);
  return optionText(item, id, englishOptions(item)?.[id] ?? english, lang);
}

/** One slider as FormQuestion sends it, "joy:3" or "fear:not_applicable", in words. */
function sliderPieces(item: FormItem, entry: string, lang: string): AnswerPiece[] {
  const [name, v] = entry.split(":");
  const label = appWords(item, name, t(`check.slider.${name}`), lang);
  const said: Shown = v === "not_applicable" || v === "na" ? appWords(item, "not_applicable", t("check.slider_na"), lang) : { text: v, lang: label.lang, english: false };
  return [label, { ...said, join: ": " }];
}

/** One answer in pieces, each in its own language, from the form's own labels. */
export function answerPieces(item: FormItem, value: AnswerValue, lang = "en"): AnswerPiece[] {
  if (item.type === "sliders") {
    const entries = Array.isArray(value) ? value.map(String) : typeof value === "object" && value !== null ? Object.entries(value).map(([k, v]) => `${k}:${v}`) : [String(value)];
    return entries.flatMap((entry) => sliderPieces(item, entry, lang));
  }
  if (item.type === "number") return [{ text: item.unit ? `${String(value)} ${item.unit}` : String(value), lang, english: false }];
  const values = Array.isArray(value) ? value : [value];
  return values.map((raw) => {
    const v = String(raw);
    if (item.type === "yesno" && v in YESNO) return appWords(item, v, t(YESNO[v]), lang);
    if (item.type === "pick_region_list") {
      // The plant list's last answer, in the words the question screen gave it (FormQuestion).
      if (v === "cant_tell") return optionText(item, v, t("check.not_sure"), lang);
      return ours(plantLabel(v) ?? v, lang);
    }
    const option = (item.options ?? []).find((o) => o.value === v);
    return option ? optionText(item, option.id, option.label, lang) : ours(v.replace(/_/g, " "), lang);
  });
}

/** The pieces as one line of text: a comma between answers, a colon inside a slider. */
export function piecesText(pieces: AnswerPiece[]): string {
  return pieces.map((p, i) => (i === 0 ? "" : (p.join ?? ", ")) + p.text).join("");
}

/** One answer in words, from the form's own labels. */
export function answerLabel(item: FormItem, value: AnswerValue, lang = "en"): string {
  return piecesText(answerPieces(item, value, lang));
}

export interface AnswerRow {
  item_id: string;
  /** The question and the answer as plain text, in the language they are shown in. */
  text: string;
  label: string;
  /** The same two with the language each piece is in, for the screen. */
  question: Shown;
  answer: AnswerPiece[];
  feature: string | null;
}

/** The answers in the form's order, each with its question and its answer in words. A skipped
 * question is not listed, and neither is a list with nothing ticked in it. */
export function answerRows(answers: Record<string, AnswerValue>, lang = "en"): AnswerRow[] {
  const given = (value: AnswerValue | undefined) => value !== undefined && !(Array.isArray(value) && value.length === 0);
  return content.form.items
    .filter((item) => given(answers[item.id]))
    .map((item) => {
      const question = itemText(item, lang);
      const answer = answerPieces(item, answers[item.id], lang);
      return { item_id: item.id, text: question.text, label: piecesText(answer), question, answer, feature: item.feature };
    });
}
