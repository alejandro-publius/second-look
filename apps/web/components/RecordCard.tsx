"use client";

import { useState } from "react";
import type { FhirObservation } from "@/lib/api";
import { t } from "@/lib/t";

type Coding = { system?: string; code?: string; display?: string };
type CodeableConcept = { coding?: Coding[]; text?: string };
type Quantity = { value?: number; unit?: string; code?: string };
type Ref = { reference?: string; display?: string };
type Period = { start?: string; end?: string };

// Our emitters (core/fhir_emit.py and worker/src/core/fhir_emit.ts) write the observer score into
// the narrative, not into a note, so a real volunteer record carries it only here.
const NARRATIVE_SCORE = /The observer scored (\d+) of (\d+) on this feature, tested (\d{4}-\d{2}-\d{2})\./;

function concept(c: unknown): string {
  const cc = c as CodeableConcept | undefined;
  if (!cc) return "";
  if (cc.text) return cc.text;
  const first = cc.coding?.[0];
  return first?.display ?? first?.code ?? "";
}

function refText(r: unknown): string {
  const list = Array.isArray(r) ? (r as Ref[]) : r ? [r as Ref] : [];
  return list.map((x) => x.display ?? x.reference ?? "").filter(Boolean).join(", ");
}

function valueOf(o: FhirObservation): string {
  if ("valueQuantity" in o) {
    const q = o.valueQuantity as Quantity;
    return `${q.value ?? ""} ${q.unit ?? q.code ?? ""}`.trim();
  }
  if ("valueCodeableConcept" in o) return concept(o.valueCodeableConcept);
  if ("valueString" in o) return String(o.valueString);
  if ("valueBoolean" in o) return String(o.valueBoolean);
  if ("valueInteger" in o) return String(o.valueInteger);
  return "";
}

/**
 * The parts of a record that gives no single value, such as a lab's average, maximum and minimum
 * for a year, or the answers to one of our questions that takes more than one. Each part is shown
 * as the record gives it: its name, then its value. Nothing here judges a number.
 */
export function componentsOf(o: FhirObservation): { name: string; value: string }[] {
  const list = Array.isArray(o.component) ? (o.component as FhirObservation[]) : [];
  return list
    .map((c) => ({ name: concept(c.code), value: valueOf(c) }))
    .filter((c) => c.name !== "" || c.value !== "");
}

/** The names a record gives its performers. A display that only repeats the reference is no name. */
function performerNames(o: FhirObservation): string {
  const list = Array.isArray(o.performer) ? (o.performer as Ref[]) : [];
  return list
    .map((x) => (x.display && x.display !== x.reference ? x.display : ""))
    .filter(Boolean)
    .join(", ");
}

/** A FHIR date or dateTime in words, in the reader's locale. A bare date is read in UTC so it never slips a day. */
export function readableTime(value: unknown): string {
  if (typeof value !== "string" || value === "") return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  if (value.includes("T")) return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return d.toLocaleDateString(undefined, { dateStyle: "medium", timeZone: "UTC" });
  return value;
}

/**
 * When the record was made: its one moment, or the span of time it covers when it gives a period
 * in place of a moment, as a lab's figures for a whole year do.
 */
export function whenOf(o: FhirObservation): string {
  const moment = readableTime(o.effectiveDateTime);
  if (moment) return moment;
  const period = o.effectivePeriod as Period | undefined;
  const start = readableTime(period?.start);
  const end = readableTime(period?.end);
  if (start && end) return t("two.period", { start, end });
  if (start) return t("two.period_from", { start });
  if (end) return t("two.period_until", { end });
  return readableTime(o.issued);
}

export function observerScore(o: FhirObservation): string | null {
  const notes = Array.isArray(o.note) ? (o.note as { text?: string }[]) : [];
  const ext = Array.isArray(o.extension) ? (o.extension as { url?: string; valueString?: string }[]) : [];
  const fromExt = ext.find((e) => e.url?.toLowerCase().includes("observer"))?.valueString;
  if (fromExt) return fromExt;
  if (notes[0]?.text) return notes[0].text;
  const div = (o.text as { div?: unknown } | undefined)?.div;
  const m = typeof div === "string" ? NARRATIVE_SCORE.exec(div) : null;
  return m ? t("record.score_line", { correct: m[1], total: m[2], when: readableTime(m[3]) }) : null;
}

/** True when both records are about the same place, ask the same thing and give the same answer. */
export function sameReading(a: FhirObservation, b: FhirObservation): boolean {
  const where = (o: FhirObservation) => (o.subject as Ref | undefined)?.reference ?? "";
  return (
    where(a) !== "" &&
    where(a) === where(b) &&
    concept(a.code) === concept(b.code) &&
    valueOf(a) !== "" &&
    valueOf(a) === valueOf(b)
  );
}

/**
 * One shared card for any FHIR Observation: theirs from the lab, ours from a volunteer. It shows what
 * a person needs to compare the two; the raw values stay in View as FHIR.
 */
export function RecordCard({
  observation,
  heading,
  performer,
  performerFallback,
  place,
  note,
}: {
  observation: FhirObservation;
  heading: string;
  /** Shown in place of whatever the record says of its performer. */
  performer?: string;
  /** Shown only when the record gives its performer no name. */
  performerFallback?: string;
  /** The place by name, when the API read it from the record, in place of a raw Location id. */
  place?: string | null;
  /** A line shown first in the card, such as the label on an example record. */
  note?: string;
}) {
  const [showJson, setShowJson] = useState(false);
  const score = observerScore(observation);
  const method = concept(observation.method);
  const value = valueOf(observation);
  const parts = value ? [] : componentsOf(observation);
  return (
    <section className="card stack" aria-label={heading}>
      <h2>{heading}</h2>
      {note ? <p className="notice notice-warn">{note}</p> : null}
      <dl>
        <div>
          <dt className="small muted">{t("record.code")}</dt>
          <dd>{concept(observation.code) || t("spot.none")}</dd>
        </div>
        <div>
          <dt className="small muted">{t("record.value")}</dt>
          {parts.length > 0 ? (
            parts.map((part, i) => (
              <dd key={`${i}-${part.name}`}>
                {part.name} <strong>{part.value}</strong>
              </dd>
            ))
          ) : (
            <dd>
              <strong>{value || t("spot.none")}</strong>
            </dd>
          )}
        </div>
        <div>
          <dt className="small muted">{t("record.when")}</dt>
          <dd>{whenOf(observation) || t("spot.none")}</dd>
        </div>
        <div>
          <dt className="small muted">{t("record.subject")}</dt>
          <dd>{place || refText(observation.subject) || t("spot.none")}</dd>
        </div>
        <div>
          <dt className="small muted">{t("record.performer")}</dt>
          <dd>{performer ?? (performerNames(observation) || performerFallback || refText(observation.performer) || t("spot.none"))}</dd>
        </div>
        {method ? (
          <div>
            <dt className="small muted">{t("record.method")}</dt>
            <dd>{method}</dd>
          </div>
        ) : null}
        {score ? (
          <div className="record-score">
            <dt className="small muted">{t("record.observer_score")}</dt>
            <dd>{score}</dd>
          </div>
        ) : null}
      </dl>
      <button type="button" className="btn btn-secondary" aria-expanded={showJson} onClick={() => setShowJson((s) => !s)}>
        {showJson ? t("spot.hide_fhir") : t("spot.view_fhir")}
      </button>
      {showJson ? <pre className="code">{JSON.stringify(observation, null, 2)}</pre> : null}
    </section>
  );
}
