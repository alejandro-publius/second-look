"use client";

import { useState } from "react";
import { api, type FhirValidationOut } from "@/lib/api";
import { t } from "@/lib/t";

function day(iso: string | undefined): string {
  const d = new Date(iso ?? "");
  return Number.isNaN(d.getTime()) ? (iso ?? "?") : d.toLocaleDateString("en-US", { dateStyle: "medium", timeZone: "UTC" });
}

/**
 * View as FHIR: the JSON, a badge with the guide commit and the validator verdict, a copyable curl
 * line. curl is null for a record made on this phone: it has no address to fetch, and the validator
 * in CI never saw it, so the badge speaks of walk records made the same way (REVIEW_03 R31).
 */
export function FhirView({ load, curl }: { load: () => Promise<unknown>; curl: string | null }) {
  const [open, setOpen] = useState(false);
  const [json, setJson] = useState<string | null>(null);
  const [validation, setValidation] = useState<FhirValidationOut | null | "down">(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (json === null) {
      try {
        const data = await load();
        setJson(JSON.stringify(data, null, 2));
      } catch {
        setError(t("error.network"));
      }
      try {
        setValidation(await api.fhirValidation());
      } catch {
        setValidation("down");
      }
    }
  }

  async function copy() {
    if (curl === null) return;
    try {
      await navigator.clipboard.writeText(curl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  const badge =
    validation && validation !== "down" && curl === null ? (
      validation.errors === 0 && (validation.walk_records_validated ?? 0) > 0 ? (
        <span className="badge badge-ok" data-testid="fhir-badge">
          {t("walk.validated_like", { date: day(validation.ran_at_utc) })}
        </span>
      ) : null
    ) : validation && validation !== "down" ? (
      <span className={validation.errors === 0 ? "badge badge-ok" : "badge badge-bad"} data-testid="fhir-badge">
        {t("spot.validated_against", {
          commit: validation.ig_commit ?? "?",
          verdict: validation.errors === 0 ? t("spot.validation_pass") : t("spot.validation_fail", { errors: validation.errors ?? "?" }),
        })}
      </span>
    ) : validation === "down" ? (
      <span className="badge badge-warn">{t("spot.validation_unknown")}</span>
    ) : null;

  return (
    <div className="stack">
      <button type="button" className="btn btn-secondary" aria-expanded={open} onClick={() => void toggle()}>
        {open ? t("spot.hide_fhir") : t("spot.view_fhir")}
      </button>
      {open ? (
        <div className="stack">
          {badge}
          {curl === null ? (
            <p className="small muted">{t("walk.no_curl")}</p>
          ) : (
            <>
              <label className="field">
                <span className="field-label">{t("spot.curl_label")}</span>
                <pre className="code">{curl}</pre>
              </label>
              <div className="btn-row">
                <button type="button" className="btn btn-secondary" onClick={() => void copy()}>
                  {copied ? t("end.copied") : t("spot.curl")}
                </button>
              </div>
            </>
          )}
          {error ? <p className="notice notice-bad">{error}</p> : null}
          {json !== null ? <pre className="code">{json}</pre> : error ? null : <p className="muted">{t("spot.loading")}</p>}
        </div>
      ) : null}
    </div>
  );
}
