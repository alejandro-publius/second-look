// The creek check and the walks in the official app's own languages (UPDATE_32 section 2).
// Mirrored questions and answers come from the app's own translations (content/app_strings.json),
// and so do the few buttons and labels the app has its own word for: Back, Next, Send and the
// three labels of a pin (uiText below). A translation whose meaning was found to differ from the
// English falls back to English, and so do our own words around the questions, which have no
// checked translation yet. A question, answer, note or follow-up shown in English inside another
// language carries a small English tag; a button in English carries lang="en" for screen readers.
import { useSyncExternalStore } from "react";
import { content, type FormItem, type FormSection } from "./content";

export const LANG_KEY = "sl.check_lang";
const EVENT = "sl-check-lang";

/** Each language by its own name, as a volunteer would look for it. */
export const LANG_NAMES: Record<string, string> = {
  en: "English",
  pt: "Português",
  nl: "Nederlands",
  no: "Norsk",
  fr: "Français",
  it: "Italiano",
  el: "Ελληνικά",
};

export function checkLanguages(): string[] {
  return content.app_strings.languages.filter(
    (l) => l in content.app_strings.strings,
  );
}

// The choice when this browser refuses storage, so it lasts until the page closes.
let chosen: string | null = null;

/**
 * The first of the browser's own languages that the check offers, or null. The phone lists its
 * languages in the order its owner likes them, such as pt-PT then en. Only the part before the
 * first hyphen counts, and the two written forms of Norwegian, nb and nn, are the app's "no".
 */
export function browserLang(): string | null {
  try {
    const offered = checkLanguages();
    const tags =
      navigator.languages && navigator.languages.length > 0
        ? navigator.languages
        : [navigator.language];
    for (const tag of tags) {
      const first = String(tag ?? "")
        .toLowerCase()
        .split("-")[0];
      const lang = first === "nb" || first === "nn" ? "no" : first;
      if (offered.includes(lang)) return lang;
    }
  } catch {
    // No navigator here: no language to go by.
  }
  return null;
}

/** A stored choice wins, then a choice made on this page, then the browser's language, then English. */
export function getCheckLang(): string {
  try {
    const v = localStorage.getItem(LANG_KEY);
    if (v && checkLanguages().includes(v)) return v;
  } catch {
    // Storage blocked: the choice made on this page, else the browser's language.
  }
  return chosen ?? browserLang() ?? "en";
}

export function setCheckLang(lang: string): void {
  if (!checkLanguages().includes(lang)) return;
  chosen = lang;
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    // Storage blocked: kept in memory above.
  }
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** The chosen language, remembered on this phone, and a setter. With no choice yet it is the
 * browser's own language when the check offers it. English on the server render. */
export function useCheckLang(): [string, (lang: string) => void] {
  const lang = useSyncExternalStore(subscribe, getCheckLang, () => "en");
  return [lang, setCheckLang];
}

/** A string to show, the language it is in, and whether it is English standing in for a translation. */
export interface Shown {
  text: string;
  lang: string;
  english: boolean;
}

function fallenBack(lang: string, key: string): boolean {
  return Boolean(content.app_strings.fallback[lang]?.[key]);
}

function pick(
  lang: string,
  key: string,
  translated: string | undefined,
  english: string,
): Shown {
  if (lang === "en") return { text: english, lang: "en", english: false };
  if (translated && !fallenBack(lang, key))
    return { text: translated, lang, english: false };
  return { text: english, lang: "en", english: true };
}

export function itemText(item: FormItem, lang: string): Shown {
  const q = content.app_strings.strings[lang]?.items[item.id];
  return pick(lang, `${item.id}.text`, q?.text, item.text);
}

/** An answer's words. For a yes or no item the option id is the stored value: present, absent, cant_tell. */
export function optionText(
  item: FormItem,
  optionId: string,
  english: string,
  lang: string,
): Shown {
  const q = content.app_strings.strings[lang]?.items[item.id];
  return pick(
    lang,
    `${item.id}.option:${optionId}`,
    q?.options?.[optionId],
    english,
  );
}

export function optionDescription(
  item: FormItem,
  optionId: string,
  english: string,
  lang: string,
): Shown {
  const q = content.app_strings.strings[lang]?.items[item.id];
  return pick(
    lang,
    `${item.id}.description:${optionId}`,
    q?.descriptions?.[optionId],
    english,
  );
}

/** The app's own English answers for this item (yes, no and not sure; the feelings), or null. */
export function englishOptions(item: FormItem): Record<string, string> | null {
  return content.app_strings.strings.en?.items[item.id]?.options ?? null;
}

/** The buttons and labels the app has its own word for (UI in scripts/app_strings.py). */
export type UiKey =
  | "back"
  | "next"
  | "send"
  | "latitude"
  | "longitude"
  | "spot_name";

/**
 * A button or label of ours in the app's own word for it. `english` is our own English, which
 * English always shows: the app's English is never shown, as one of its labels has a typo.
 */
export function uiText(key: UiKey, english: string, lang: string): Shown {
  const block = content.app_strings.strings[lang] as
    | { ui?: Record<string, string> }
    | undefined;
  return pick(lang, `ui:${key}`, block?.ui?.[key], english);
}

export function sectionTitle(section: FormSection, lang: string): Shown {
  const t = content.app_strings.strings[lang]?.sections[section.id];
  return pick(lang, `section:${section.id}`, t, section.title);
}

/** An item's answers in the chosen language, as the rating check offers them again. */
export function shownOptions(item: FormItem | undefined, lang: string) {
  if (!item) return [];
  return (item.options ?? []).map((o) => {
    const label = optionText(item, o.id, o.label, lang);
    const description = o.description
      ? optionDescription(item, o.id, o.description, lang).text
      : undefined;
    return { ...o, label: label.text, description, lang: label.lang };
  });
}
