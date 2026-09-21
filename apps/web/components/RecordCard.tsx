"use client";

import { useState } from "react";
import type { FhirObservation } from "@/lib/api";
import { t } from "@/lib/t";

type Coding = { system?: string; code?: string; display?: string };
type CodeableConcept = { coding?: Coding[]; text?: string };
type Quantity = { value?: number; unit?: string; code?: string };
type Ref = { reference?: string; display?: string };

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

function observerScore(o: FhirObservation): string | null {
  const notes = Array.isArray(o.note) ? (o.note as { text?: string }[]) : [];
  const ext = Array.isArray(o.extension) ? (o.extension as { url?: string; valueString?: string }[]) : [];
  const fromExt = ext.find((e) => e.url?.toLowerCase().includes("observer"))?.valueString;
  return fromExt ?? notes[0]?.text ?? null;
}

/** One shared card for any FHIR Observation: theirs from the lab, ours from a volunteer. */
export function RecordCard({ observation, heading }: { observation: FhirObservation; heading: string }) {
  const [showJson, setShowJson] = useState(false);
  const score = observerScore(observation);
  return (
    <section className="card stack" aria-label={heading}>
      <h2>{heading}</h2>
      <dl>
        <dt className="small muted">{t("record.code")}</dt>
        <dd>{concept(observation.code) || t("spot.none")}</dd>
        <dt className="small muted">{t("record.value")}</dt>
        <dd>
          <strong>{valueOf(observation) || t("spot.none")}</strong>
        </dd>
        <dt className="small muted">{t("record.when")}</dt>
        <dd>{String(observation.effectiveDateTime ?? observation.issued ?? t("spot.none"))}</dd>
        <dt className="small muted">{t("record.subject")}</dt>
        <dd>{refText(observation.subject) || t("spot.none")}</dd>
        <dt className="small muted">{t("record.performer")}</dt>
        <dd>{refText(observation.performer) || t("spot.none")}</dd>
        <dt className="small muted">{t("record.method")}</dt>
        <dd>{concept(observation.method) || t("spot.none")}</dd>
        {score ? (
          <>
            <dt className="small muted">{t("record.observer_score")}</dt>
            <dd>{score}</dd>
          </>
        ) : null}
        <dt className="small muted">{t("record.status")}</dt>
        <dd>{String(observation.status ?? t("spot.none"))}</dd>
      </dl>
      <button type="button" className="btn btn-secondary" aria-expanded={showJson} onClick={() => setShowJson((s) => !s)}>
        {showJson ? t("spot.hide_fhir") : t("spot.view_fhir")}
      </button>
      {showJson ? <pre className="code">{JSON.stringify(observation, null, 2)}</pre> : null}
    </section>
  );
}
