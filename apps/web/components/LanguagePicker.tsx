"use client";

import { checkLanguages, LANG_NAMES, useCheckLang } from "@/lib/lang";
import { t } from "@/lib/t";

/**
 * The language of the creek check's questions, remembered on this phone (UPDATE_32 section 2).
 * The questions and answers are the official app's own, in its own translations; our own words
 * around them stay English, each marked, until a person has checked a translation.
 *
 * A walk shows the two parts apart (audit finding phone-ux-languages-5): the list alone right
 * under the walk's title, where the first screen shows it, under a short visible label (WCAG
 * 3.3.2), and the note further down, below Start, where it pushes nothing off the screen.
 */
export function LanguagePicker({
  part = "all",
}: {
  part?: "all" | "list" | "note";
}) {
  const [lang, setLang] = useCheckLang();
  const note = (
    <p className="small muted" data-testid="language-note">
      {t("check.lang_note")}
    </p>
  );
  if (part === "note") return note;
  const list = (
    <label className="field">
      <span className={part === "list" ? "field-label small" : "field-label"}>
        {t(part === "list" ? "check.lang_label_short" : "check.lang_label")}
      </span>
      <span className="select-wrap">
        <select
          className="text-input"
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          name="check-language"
        >
          {checkLanguages().map((l) => (
            <option key={l} value={l} lang={l}>
              {LANG_NAMES[l] ?? l}
            </option>
          ))}
        </select>
      </span>
    </label>
  );
  if (part === "list")
    return (
      <div className="lang-compact" data-testid="language-picker">
        {list}
      </div>
    );
  return (
    <div className="stack" data-testid="language-picker">
      {list}
      {note}
    </div>
  );
}

/** Marks English words shown inside another language, for sighted readers and screen readers alike. */
export function EnglishTag() {
  return (
    <span className="badge badge-lang" lang="en" data-testid="english-tag">
      {t("check.english_tag")}
    </span>
  );
}
