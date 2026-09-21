"use client";

import { useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { t } from "@/lib/t";

/**
 * Consent: the what, what is stored, not advice, contact. Two required checkboxes. The `website`
 * text input is the bot trap: off screen, out of the tab order, sent as hidden_field.
 */
export function Consent({ onStart }: { onStart: (hiddenField: string) => void }) {
  const [agree, setAgree] = useState(false);
  const [adult, setAdult] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!agree || !adult) {
      setError(t("consent.need_both"));
      return;
    }
    const form = e.currentTarget;
    const hp = form.elements.namedItem("website") as HTMLInputElement | null;
    onStart(hp?.value ?? "");
  }

  return (
    <form className="stack" onSubmit={submit} noValidate>
      <FocusHeading>{t("consent.title")}</FocusHeading>
      <p>{t("consent.what")}</p>
      <p>{t("consent.stored")}</p>
      <p>{t("consent.not_advice")}</p>
      <p className="small muted">{t("consent.contact")}</p>
      <div className="hp" aria-hidden="true">
        <label htmlFor="website">{t("consent.website_label")}</label>
        <input id="website" name="website" type="text" tabIndex={-1} autoComplete="off" defaultValue="" />
      </div>
      <label className="check">
        <input type="checkbox" name="agree" checked={agree} onChange={(e) => setAgree(e.target.checked)} required />
        <span>{t("consent.check_consent")}</span>
      </label>
      <label className="check">
        <input type="checkbox" name="adult" checked={adult} onChange={(e) => setAdult(e.target.checked)} required />
        <span>{t("consent.check_age")}</span>
      </label>
      {error ? (
        <p className="notice notice-warn" role="alert">
          {error}
        </p>
      ) : null}
      <button type="submit" className="btn btn-block">
        {t("consent.start")}
      </button>
    </form>
  );
}
