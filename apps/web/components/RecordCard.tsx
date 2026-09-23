"use client";

import { useState } from "react";
import type { FhirObservation } from "@/lib/api";
import { t } from "@/lib/t";

type Coding = { system?: string; code?: string; display?: string };
type CodeableConcept = { coding?: Coding[]; text?: string };
type Quantity = { value?: number; unit?: string; code?: string };
type Ref = { reference?: string; display?: string };

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

/** A FHIR date or dateTime in words, in the reader's locale. A bare date is read in UTC so it never slips a day. */
export function readableTime(value: unknown): string {
  if (typeof value !== "string" || value === "") return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  if (value.includes("T")) return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return d.toLocaleDateString(undefined, { dateStyle: "medium", timeZone: "UTC" });
  return value;
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
export function RecordCard({ observation, heading, performer }: { observation: FhirObservation; heading: string; performer?: string }) {
  const [showJson, setShowJson] = useState(false);
  const score = observerScore(observation);
  const method = concept(observation.method);
  return (
    <section className="card stack" aria-label={heading}>
      <h2>{heading}</h2>
      <dl>
        <div>
          <dt className="small muted">{t("record.code")}</dt>
          <dd>{concept(observation.code) || t("spot.none")}</dd>
        </div>
        <div>
          <dt className="small muted">{t("record.value")}</dt>
          <dd>
            <strong>{valueOf(observation) || t("spot.none")}</strong>
          </dd>
        </div>
        <div>
          <dt className="small muted">{t("record.when")}</dt>
          <dd>{readableTime(observation.effectiveDateTime ?? observation.issued) || t("spot.none")}</dd>
        </div>
        <div>
          <dt className="small muted">{t("record.subject")}</dt>
          <dd>{refText(observation.subject) || t("spot.none")}</dd>
        </div>
        <div>
          <dt className="small muted">{t("record.performer")}</dt>
          <dd>{performer ?? (refText(observation.performer) || t("spot.none"))}</dd>
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
