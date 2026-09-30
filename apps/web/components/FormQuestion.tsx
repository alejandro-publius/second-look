"use client";

import { useEffect, useRef, useState } from "react";
import { GlossaryAside } from "./Glossary";
import { EnglishTag } from "./LanguagePicker";
import type { AnswerValue } from "@/lib/api";
import {
  content,
  featureById,
  glossaryFor,
  plantRegions,
  type FormItem,
} from "@/lib/content";
import {
  englishOptions,
  itemText,
  optionDescription,
  optionText,
  sectionTitle,
  uiText,
  type Shown,
} from "@/lib/lang";
import { t } from "@/lib/t";

/** A question longer than this many letters is set one size down, so its answers fit. */
const LONG_QUESTION = 90;

/** A string in the language it is in; English inside another language carries its tag. */
function Words({ shown }: { shown: Shown }) {
  return (
    <>
      <span lang={shown.lang}>{shown.text}</span>
      {shown.english ? (
        <>
          {" "}
          <EnglishTag />
        </>
      ) : null}
    </>
  );
}

/** Glossary toggles for every technical word in an item's text, plus the feature's own term. */
function GlossaryLinks({ item }: { item: FormItem }) {
  const hits: { term: string; plain: string }[] = [];
  const lower = item.text.toLowerCase();
  for (const g of content.glossary) {
    if (lower.includes(g.term.toLowerCase())) hits.push(g);
  }
  if (item.feature) {
    const f = featureById(item.feature);
    if (
      f &&
      !hits.some((h) => h.term.toLowerCase() === f.glossary_term.toLowerCase())
    ) {
      hits.push({
        term: f.glossary_term,
        plain: glossaryFor(f.glossary_term) ?? f.plain,
      });
    }
  }
  if (hits.length === 0) return null;
  return (
    <div>
      {hits.map((h) => (
        <GlossaryAside key={h.term} term={h.term} definition={h.plain} />
      ))}
    </div>
  );
}

/**
 * One form item rendered by type. Choice and yes/no move on at once; the rest need Next.
 *
 * plantRegion says which region's plant list "Which ones?" offers (critic round 14 B03, round 15
 * F04): the region pack the spot is in, null when it is in none, such as a video walk's creek in
 * Russia, the UK or Oregon, and undefined when this device does not know where the spot is (a
 * saved spot), which offers every list as before. The screen always says which region a list is
 * for, and a creek outside every region gets no list, only Can't tell and None of these.
 */
export function FormQuestion({
  item,
  value,
  onAnswer,
  onBack,
  onSkip,
  plantRegion,
  lang = "en",
}: {
  item: FormItem;
  value: AnswerValue | undefined;
  onAnswer: (v: AnswerValue) => void;
  onBack: () => void;
  onSkip: () => void;
  plantRegion?: string | null;
  /** The language of the questions (UPDATE_32 section 2); the app's own translations. */
  lang?: string;
}) {
  const [draft, setDraft] = useState<AnswerValue | undefined>(value);
  // WCAG 2.4.3: each new question's heading takes focus, as the quick check's does (FocusHeading),
  // so a keyboard or screen reader user lands on the question and not at the top of the page.
  // The check and the walks key this component by item.id, so this runs once per question.
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [item.id]);
  const section = content.form.sections.find((s) => s.id === item.section);
  const unverified = !item.verified_against_app;
  const english = englishOptions(item);
  const other = lang !== "en";
  // Our own words (buttons, notes) have no checked translation: English, marked, in another language.
  const ours = other ? { lang: "en" } : {};
  const answerWords = (id: string, fallback: string) =>
    optionText(item, id, english?.[id] ?? fallback, lang);
  const shownText = itemText(item, lang);

  function regionList(): {
    options: { id: string; label: string; value: string }[];
    note: string;
    empty: boolean;
  } {
    const listed = plantRegions();
    const here =
      plantRegion === undefined
        ? listed
        : listed.filter((r) => r.region === plantRegion);
    const options: { id: string; label: string; value: string }[] = [];
    for (const region of here) {
      for (const p of region.invasive_plants ?? []) {
        options.push({
          id: p.latin_name,
          label: `${p.common_name} (${p.latin_name})`,
          value: p.latin_name,
        });
      }
    }
    // The last answer is worded in another language as the app words it on its own invasive
    // species question, whose placeholder "Which ones?" is (scripts/app_strings.py).
    options.push({
      id: "cant_tell",
      label: t("check.not_sure"),
      value: "cant_tell",
    });
    const names = (regions: { name: string }[]) =>
      regions.map((r) => r.name).join(" and ");
    if (here.length > 0)
      return {
        options,
        note: t("check.region_list_for", { region: names(here) }),
        empty: false,
      };
    // A spot in a region pack with no list yet, or no list anywhere: the old line.
    const inPack = plantRegion
      ? Object.values(content.regions).some((r) => r.region === plantRegion)
      : false;
    if (inPack || listed.length === 0)
      return { options, note: t("check.region_list_empty"), empty: true };
    return {
      options,
      note: t("check.region_list_elsewhere", { regions: names(listed) }),
      empty: true,
    };
  }

  // The app has a title for two of our five sections. The other three titles are our own English
  // words, and right above a translated question an English line such as "How is the water?" read
  // as the question shown twice, so another language leaves it out (audit finding
  // phone-ux-languages-6).
  const sectionWords = section ? sectionTitle(section, lang) : null;
  // The app's longest questions run six or seven lines at the heading's size and push the last
  // answer off a phone's first screen, so a long one is set one size down (finding 4).
  const long = shownText.text.length > LONG_QUESTION;

  const head = (
    <>
      {sectionWords && !sectionWords.english ? (
        <p className="small muted" data-testid="section-line">
          <Words shown={sectionWords} />
        </p>
      ) : null}
      <h1
        ref={heading}
        tabIndex={-1}
        id="question"
        className={long ? "question-long" : undefined}
      >
        <span lang={shownText.lang}>{shownText.text}</span>
        {item.unit ? ` (${item.unit})` : ""}
        {shownText.english ? (
          <>
            {" "}
            <EnglishTag />
          </>
        ) : null}
      </h1>
      {unverified ? (
        <span className="badge badge-warn">{t("check.unverified")}</span>
      ) : null}
      {other ? (
        <div lang="en">
          <GlossaryLinks item={item} />
        </div>
      ) : (
        <GlossaryLinks item={item} />
      )}
    </>
  );

  // Back and Next are in the app's own words (audit finding phone-ux-languages-3). Skip and
  // None of these have no app word, so they stay English and say so to a screen reader.
  const back = uiText("back", t("check.back"), lang);
  const next = uiText("next", t("check.next"), lang);
  const nav = (extra?: React.ReactNode) => (
    <div className="btn-row">
      <button
        type="button"
        className="btn btn-secondary"
        onClick={onBack}
        lang={back.lang}
      >
        {back.text}
      </button>
      {extra}
    </div>
  );

  switch (item.type) {
    case "choice":
      return (
        <div className="stack">
          {head}
          <div className="option-list" role="group" aria-labelledby="question">
            {(item.options ?? []).map((o) => (
              <button
                key={o.id}
                type="button"
                className="option"
                aria-pressed={value === o.value}
                onClick={() => onAnswer(o.value)}
              >
                <Words shown={optionText(item, o.id, o.label, lang)} />
                {o.description ? (
                  <span className="small muted option-description">
                    {" "}
                    <Words
                      shown={optionDescription(item, o.id, o.description, lang)}
                    />
                  </span>
                ) : null}
              </button>
            ))}
          </div>
          {nav()}
        </div>
      );
    case "yesno":
      return (
        <div className="stack">
          {head}
          <div className="option-list" role="group" aria-labelledby="question">
            {[
              ["present", t("check.yes")],
              ["absent", t("check.no")],
              ["cant_tell", t("check.not_sure")],
            ].map(([v, label]) => (
              <button
                key={v}
                type="button"
                className="option"
                aria-pressed={value === v}
                onClick={() => onAnswer(v)}
              >
                <Words shown={answerWords(v, label)} />
              </button>
            ))}
          </div>
          {nav()}
        </div>
      );
    case "multi":
    case "pick_region_list": {
      const plants = item.type === "pick_region_list" ? regionList() : null;
      const options = plants ? plants.options : (item.options ?? []);
      const chosen = Array.isArray(draft) ? (draft as string[]) : [];
      const toggle = (v: string) =>
        setDraft(
          chosen.includes(v) ? chosen.filter((x) => x !== v) : [...chosen, v],
        );
      return (
        <div className="stack">
          {head}
          {plants ? (
            <p
              className={plants.empty ? "notice notice-warn" : "small muted"}
              data-testid="region-list-note"
              {...ours}
            >
              {/* One child, so the notice's row keeps the tag on the note's last line. */}
              <span>
                {plants.note}
                {other ? (
                  <>
                    {" "}
                    <EnglishTag />
                  </>
                ) : null}
              </span>
            </p>
          ) : null}
          <div className="option-list" role="group" aria-labelledby="question">
            {options.map((o) => (
              <label key={o.id} className="option">
                <input
                  type="checkbox"
                  checked={chosen.includes(o.value)}
                  onChange={() => toggle(o.value)}
                />
                <span>
                  {!plants || o.id === "cant_tell" ? (
                    <Words shown={optionText(item, o.id, o.label, lang)} />
                  ) : (
                    // A plant's name is from our own region list: English, and the note above
                    // the list carries the English tag for all of them.
                    <span {...ours}>{o.label}</span>
                  )}
                </span>
              </label>
            ))}
          </div>
          {nav(
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onSkip}
                {...ours}
              >
                {t("check.none_of_these")}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => onAnswer(chosen)}
                lang={next.lang}
              >
                {next.text}
              </button>
            </>,
          )}
        </div>
      );
    }
    case "number": {
      const numberLabel = (
        <span className="field-label" {...ours}>
          {t("check.number_label", { unit: item.unit ?? "" })}
          {other ? (
            <>
              {" "}
              <EnglishTag />
            </>
          ) : null}
        </span>
      );
      const text =
        typeof draft === "number"
          ? String(draft)
          : typeof draft === "string"
            ? draft
            : "";
      return (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            const n = Number(text);
            if (text.trim() === "" || !Number.isFinite(n)) onSkip();
            else onAnswer(n);
          }}
        >
          {head}
          <label className="field">
            {numberLabel}
            <input
              className="text-input"
              type="number"
              inputMode="decimal"
              step="any"
              min={0}
              value={text}
              onChange={(e) => setDraft(e.target.value)}
              name={item.id}
            />
          </label>
          {nav(
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onSkip}
                {...ours}
              >
                {t("check.skip")}
              </button>
              <button type="submit" className="btn" lang={next.lang}>
                {next.text}
              </button>
            </>,
          )}
        </form>
      );
    }
    case "sliders": {
      // The API takes sliders as a list like ["joy:3", "fear:not_applicable"] (content/form.yaml,
      // apps/api/check.py, worker/src/check.ts). The screen works on a map; this reads a list back.
      // A slider is in the map only once the person moves it or ticks Not applicable. One left
      // where it starts is not a 0: it is not sent and not in the record (CRITIC_06 H03).
      const current: Record<string, number | string> = {};
      if (Array.isArray(draft)) {
        for (const entry of draft) {
          const [k, v] = String(entry).split(":");
          current[k] = v === "not_applicable" ? "na" : Number(v);
        }
      } else if (draft && typeof draft === "object")
        Object.assign(current, draft);
      const set = (k: string, v: number | string | undefined) => {
        const next = { ...current };
        if (v === undefined) delete next[k];
        else next[k] = v;
        setDraft(next);
      };
      return (
        <div className="stack">
          {head}
          <div className="stack" role="group" aria-labelledby="question">
            {(item.sliders ?? []).map((s) => {
              const v = current[s];
              const na = v === "na";
              return (
                <div key={s} className="card">
                  <div className="range-row">
                    <label htmlFor={`slider-${s}`}>
                      <Words shown={answerWords(s, t(`check.slider.${s}`))} />
                    </label>
                    <input
                      id={`slider-${s}`}
                      type="range"
                      min={0}
                      max={5}
                      step={1}
                      value={typeof v === "number" ? v : 0}
                      disabled={na}
                      onChange={(e) => set(s, Number(e.target.value))}
                    />
                    <output htmlFor={`slider-${s}`} aria-live="off">
                      {typeof v === "number" ? v : ""}
                    </output>
                  </div>
                  {item.allow_not_applicable ? (
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={na}
                        onChange={(e) =>
                          set(s, e.target.checked ? "na" : undefined)
                        }
                      />
                      <span className="small">
                        <Words
                          shown={answerWords(
                            "not_applicable",
                            t("check.slider_na"),
                          )}
                        />
                      </span>
                    </label>
                  ) : null}
                </div>
              );
            })}
          </div>
          {nav(
            <button
              type="button"
              className="btn"
              onClick={() => {
                const out = (item.sliders ?? [])
                  .filter((s) => current[s] !== undefined)
                  .map(
                    (s) =>
                      `${s}:${current[s] === "na" ? "not_applicable" : current[s]}`,
                  );
                // No slider moved: the question is left out, as Skip leaves out the others.
                if (out.length === 0) onSkip();
                else onAnswer(out);
              }}
              lang={next.lang}
            >
              {next.text}
            </button>,
          )}
        </div>
      );
    }
  }
}
