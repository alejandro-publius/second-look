"use client";

import { useState } from "react";
import type { FeatureScoreOut } from "@/lib/api";
import { featureById } from "@/lib/content";
import { siteUrl } from "@/lib/session";
import { t } from "@/lib/t";

/** Per-feature score, the share card and, once, the contributor token. Never per-photo answers. */
export function ScoreScreen({ scores, correctTotal, token, children }: { scores: FeatureScoreOut[]; correctTotal: number; token?: string; children?: React.ReactNode }) {
  const [copied, setCopied] = useState<"none" | "share" | "token">("none");
  const total = scores.reduce((n, s) => n + s.total, 0) || 16;
  const shareText = t("end.share", { correct: correctTotal, total });
  const shareUrl = `${siteUrl()}/share/${correctTotal}?src=friends`;
  const cardUrl = `/api/share/${correctTotal}`;

  async function share() {
    const nav = navigator as Navigator & { share?: (d: ShareData) => Promise<void> };
    if (nav.share) {
      try {
        await nav.share({ text: shareText, url: shareUrl });
        return;
      } catch {
        // fall through to copy
      }
    }
    await copy(`${shareText} ${shareUrl}`, "share");
  }

  async function copy(text: string, what: "share" | "token") {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(what);
      window.setTimeout(() => setCopied("none"), 2500);
    } catch {
      setCopied("none");
    }
  }

  return (
    <div className="stack">
      <p className="card">
        <strong>{t("end.total", { correct: correctTotal, total })}</strong>
      </p>
      <ul className="stack" aria-label={t("end.per_feature_label")}>
        {scores.map((s) => (
          <li key={s.feature}>{t("end.per_feature", { correct: s.correct, total: s.total, feature: featureById(s.feature)?.name ?? s.feature })}</li>
        ))}
      </ul>
      <p>{t("end.last_line")}</p>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="share-card" src={cardUrl} alt={t("end.share_card_alt", { correct: correctTotal, total })} width={1200} height={630} />
      <div className="btn-row">
        <button type="button" className="btn" onClick={share}>
          {copied === "share" ? t("end.copied") : t("end.share_button")}
        </button>
      </div>
      {token ? (
        <section className="card stack" aria-labelledby="token-title">
          <h2 id="token-title">{t("end.token_title")}</h2>
          <p className="token" data-testid="contributor-token">
            {token}
          </p>
          <p className="small">{t("end.token_note")}</p>
          <div className="btn-row">
            <button type="button" className="btn btn-secondary" onClick={() => copy(token, "token")}>
              {copied === "token" ? t("end.copied") : t("end.copy_token")}
            </button>
          </div>
        </section>
      ) : null}
      {children}
    </div>
  );
}
