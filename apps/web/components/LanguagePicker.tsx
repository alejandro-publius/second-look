"use client";

import { checkLanguages, LANG_NAMES, useCheckLang } from "@/lib/lang";
import { t } from "@/lib/t";

/**
 * The language of the creek check's questions, remembered on this phone (UPDATE_32 section 2).
 * The questions and answers are the official app's own, in its own translations; our own words
 * around them stay English, each marked, until a person has checked a translation.
 */
export function LanguagePicker() {
  const [lang, setLang] = useCheckLang();
  return (
    <div className="stack" data-testid="language-picker">
      <label className="field">
        <span className="field-label">{t("check.lang_label")}</span>
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
      </label>
      <p className="small muted">{t("check.lang_note")}</p>
    </div>
  );
}

/** Marks English words shown inside another language, for sighted readers and screen readers alike. */
export function EnglishTag() {
  return (
    <span className="badge" lang="en" data-testid="english-tag">
      {t("check.english_tag")}
    </span>
  );
}
