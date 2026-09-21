"use client";

import { useState } from "react";
import { api, type FhirValidationOut } from "@/lib/api";
import { t } from "@/lib/t";

/** View as FHIR: the JSON, a badge with the guide commit and the validator verdict, a copyable curl line. */
export function FhirView({ load, curl }: { load: () => Promise<unknown>; curl: string }) {
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
    try {
      await navigator.clipboard.writeText(curl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  const badge =
    validation && validation !== "down" ? (
      <span className={validation.errors === 0 ? "badge badge-ok" : "badge badge-bad"}>
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
          <label className="field">
            <span className="field-label">{t("spot.curl_label")}</span>
            <pre className="code">{curl}</pre>
          </label>
          <div className="btn-row">
            <button type="button" className="btn btn-secondary" onClick={() => void copy()}>
              {copied ? t("end.copied") : t("spot.curl")}
            </button>
          </div>
          {error ? <p className="notice notice-bad">{error}</p> : null}
          {json !== null ? <pre className="code">{json}</pre> : error ? null : <p className="muted">{t("spot.loading")}</p>}
        </div>
      ) : null}
    </div>
  );
}
