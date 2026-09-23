"use client";

import { useState } from "react";
import { GlossaryAside } from "./Glossary";
import type { AnswerValue } from "@/lib/api";
import { content, featureById, glossaryFor, type FormItem } from "@/lib/content";
import { t } from "@/lib/t";

/** Glossary toggles for every technical word in an item's text, plus the feature's own term. */
function GlossaryLinks({ item }: { item: FormItem }) {
  const hits: { term: string; plain: string }[] = [];
  const lower = item.text.toLowerCase();
  for (const g of content.glossary) {
    if (lower.includes(g.term.toLowerCase())) hits.push(g);
  }
  if (item.feature) {
    const f = featureById(item.feature);
    if (f && !hits.some((h) => h.term.toLowerCase() === f.glossary_term.toLowerCase())) {
      hits.push({ term: f.glossary_term, plain: glossaryFor(f.glossary_term) ?? f.plain });
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

/** One form item rendered by type. Choice and yes/no move on at once; the rest need Next. */
export function FormQuestion({ item, value, onAnswer, onBack, onSkip }: { item: FormItem; value: AnswerValue | undefined; onAnswer: (v: AnswerValue) => void; onBack: () => void; onSkip: () => void }) {
  const [draft, setDraft] = useState<AnswerValue | undefined>(value);
  const section = content.form.sections.find((s) => s.id === item.section);
  const unverified = !item.verified_against_app;

  function regionOptions(): { id: string; label: string; value: string }[] {
    const opts: { id: string; label: string; value: string }[] = [];
    for (const region of Object.values(content.regions)) {
      for (const p of region.invasive_plants ?? []) {
        opts.push({ id: p.latin_name, label: `${p.common_name} (${p.latin_name})`, value: p.latin_name });
      }
    }
    opts.push({ id: "cant_tell", label: t("check.not_sure"), value: "cant_tell" });
    return opts;
  }

  const head = (
    <>
      {section ? <p className="small muted">{section.title}</p> : null}
      <h1 tabIndex={-1} id="question">
        {item.text}
        {item.unit ? ` (${item.unit})` : ""}
      </h1>
      {unverified ? <span className="badge badge-warn">{t("check.unverified")}</span> : null}
      <GlossaryLinks item={item} />
    </>
  );

  const nav = (extra?: React.ReactNode) => (
    <div className="btn-row">
      <button type="button" className="btn btn-secondary" onClick={onBack}>
        {t("check.back")}
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
              <button key={o.id} type="button" className="option" aria-pressed={value === o.value} onClick={() => onAnswer(o.value)}>
                {o.label}
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
              <button key={v} type="button" className="option" aria-pressed={value === v} onClick={() => onAnswer(v)}>
                {label}
              </button>
            ))}
          </div>
          {nav()}
        </div>
      );
    case "multi":
    case "pick_region_list": {
      const options = item.type === "multi" ? item.options ?? [] : regionOptions();
      const chosen = Array.isArray(draft) ? (draft as string[]) : [];
      const toggle = (v: string) => setDraft(chosen.includes(v) ? chosen.filter((x) => x !== v) : [...chosen, v]);
      return (
        <div className="stack">
          {head}
          {item.type === "pick_region_list" && options.length === 1 ? <p className="notice notice-warn">{t("check.region_list_empty")}</p> : null}
          <div className="option-list" role="group" aria-labelledby="question">
            {options.map((o) => (
              <label key={o.id} className="option">
                <input type="checkbox" checked={chosen.includes(o.value)} onChange={() => toggle(o.value)} />
                <span>{o.label}</span>
              </label>
            ))}
          </div>
          {nav(
            <>
              <button type="button" className="btn btn-secondary" onClick={onSkip}>
                {t("check.none_of_these")}
              </button>
              <button type="button" className="btn" onClick={() => onAnswer(chosen)}>
                {t("check.next")}
              </button>
            </>,
          )}
        </div>
      );
    }
    case "number": {
      const text = typeof draft === "number" ? String(draft) : typeof draft === "string" ? draft : "";
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
            <span className="field-label">{t("check.number_label", { unit: item.unit ?? "" })}</span>
            <input className="text-input" type="number" inputMode="decimal" step="any" min={0} value={text} onChange={(e) => setDraft(e.target.value)} name={item.id} />
          </label>
          {nav(
            <>
              <button type="button" className="btn btn-secondary" onClick={onSkip}>
                {t("check.skip")}
              </button>
              <button type="submit" className="btn">
                {t("check.next")}
              </button>
            </>,
          )}
        </form>
      );
    }
    case "sliders": {
      // The API takes sliders as a list like ["joy:3", "fear:not_applicable"] (content/form.yaml,
      // apps/api/check.py, worker/src/check.ts). The screen works on a map; this reads a list back.
      const current: Record<string, number | string> = {};
      if (Array.isArray(draft)) {
        for (const entry of draft) {
          const [k, v] = String(entry).split(":");
          current[k] = v === "not_applicable" ? "na" : Number(v);
        }
      } else if (draft && typeof draft === "object") Object.assign(current, draft);
      const set = (k: string, v: number | string) => setDraft({ ...current, [k]: v });
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
                    <label htmlFor={`slider-${s}`}>{t(`check.slider.${s}`)}</label>
                    <input id={`slider-${s}`} type="range" min={0} max={5} step={1} value={typeof v === "number" ? v : 0} disabled={na} onChange={(e) => set(s, Number(e.target.value))} />
                    <output htmlFor={`slider-${s}`} aria-live="off">
                      {na ? "" : typeof v === "number" ? v : 0}
                    </output>
                  </div>
                  {item.allow_not_applicable ? (
                    <label className="check">
                      <input type="checkbox" checked={na} onChange={(e) => set(s, e.target.checked ? "na" : 0)} />
                      <span className="small">{t("check.slider_na")}</span>
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
                const out = (item.sliders ?? []).map((s) => {
                  const v = current[s] ?? 0;
                  return `${s}:${v === "na" ? "not_applicable" : v}`;
                });
                onAnswer(out);
              }}
            >
              {t("check.next")}
            </button>,
          )}
        </div>
      );
    }
  }
}
