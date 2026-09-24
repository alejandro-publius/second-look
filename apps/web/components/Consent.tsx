"use client";

import { useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { Button, ButtonLink } from "./ui/Button";
import { Icon } from "./ui/Icon";
import { usePanel } from "@/lib/panel";
import { t } from "@/lib/t";

/**
 * Consent: the what, what is stored, not advice, contact. Two required checkboxes. The `website`
 * text input is the bot trap: off screen, out of the tab order, hidden from screen readers, sent
 * as hidden_field.
 */
export function Consent({ onStart }: { onStart: (hiddenField: string) => void }) {
  const [agree, setAgree] = useState(false);
  const [adult, setAdult] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // One extra sentence for the panel study only (UPDATE_29 section 1), read from the link or the
  // label kept for the session.
  const panel = usePanel();

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
      <p className="small">
        <ButtonLink href="/" kind="quiet">
          <Icon name="caret-left" size={20} />
          {t("nav.back")}
        </ButtonLink>
      </p>
      <FocusHeading>{t("consent.title")}</FocusHeading>
      <p>{t("consent.what")}</p>
      <p>{t("consent.stored")}</p>
      <p>{t("consent.not_advice")}</p>
      <p>{t("consent.hosts")}</p>
      {panel ? <p data-testid="consent-panel">{t("consent.panel")}</p> : null}
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
        <div className="notice notice-warn" role="alert">
          <Icon name="warning" />
          <p>{error}</p>
        </div>
      ) : null}
      <div className="actions">
        <Button type="submit" block>
          {t("consent.start")}
        </Button>
      </div>
    </form>
  );
}
