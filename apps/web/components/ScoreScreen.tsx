"use client";

import { useState } from "react";
import { Button } from "./ui/Button";
import { Icon } from "./ui/Icon";
import { Gauge } from "./ui/Gauge";
import { Row } from "./ui/Row";
import { PhotoFrame } from "./ui/PhotoFrame";
import type { FeatureScoreOut } from "@/lib/api";
import type { WarmupItem } from "@/lib/content";
import { content, featureById } from "@/lib/content";
import { siteUrl } from "@/lib/session";
import { t } from "@/lib/t";

/**
 * The answer to the question on the poster, shown here and not on the landing page. Before the
 * test it would be a small lesson handed to both arms, which would shrink the gap the study
 * measures. It says one creek is in a more natural state, and says plainly that a photo cannot
 * tell anyone whether the water is safe.
 *
 * It never says "the one on the right". On a phone the two photographs stack, and the order they
 * were shown in may be shuffled, so the badge travels with the photograph itself.
 */
export function WarmupReveal({ pair = content.warmup }: { pair?: WarmupItem[] }) {
  return (
    <div className="card stack" aria-labelledby="warmup-reveal">
      <h2 id="warmup-reveal" className="small">{t("warmup.reveal_title")}</h2>
      <div className="pair">
        {pair.map((w) => (
          <div key={w.id} data-testid={w.more_natural ? "reveal-natural" : "reveal-modified"}>
            <PhotoFrame id={w.photo_id} />
            <p className="small">
              <strong>{t(w.more_natural ? "warmup.reveal_badge" : "warmup.reveal_other")}</strong>{" "}
              {t(w.more_natural ? "warmup.reveal_natural_note" : "warmup.reveal_modified_note")}
            </p>
          </div>
        ))}
      </div>
      <p>{t("warmup.reveal_point")}</p>
      <p className="small muted">{t("warmup.reveal_limit")}</p>
    </div>
  );
}

/**
 * One gauge per feature, the same object as the progress bar in the test. Then the sentence that
 * says what the score is for, then the share card. No confetti. Never per-photo answers.
 */
export function ScoreScreen({ scores, correctTotal, token, children }: { scores: FeatureScoreOut[]; correctTotal: number; token?: string; children?: React.ReactNode }) {
  const [copied, setCopied] = useState<"none" | "share" | "token" | "failed">("none");
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
      setCopied("failed");
    }
  }

  return (
    <div className="stack">
      <Gauge value={correctTotal} total={total} countText={t("end.total", { correct: correctTotal, total })} />
      <div className="card" aria-label={t("end.per_feature_label")} role="group">
        {scores.map((s) => {
          const name = featureById(s.feature)?.name ?? s.feature;
          return <Row key={s.feature} label={name} end={<Gauge size="mark" value={s.correct} total={s.total} />} />;
        })}
      </div>
      <WarmupReveal />
      <p>{t("end.score_for")}</p>
      <p>{t("end.last_line")}</p>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="share-card" src={cardUrl} alt={t("end.share_card_alt", { correct: correctTotal, total })} width={1200} height={630} />
      <div className="actions">
        <Button block onClick={share}>
          {copied === "share" ? t("end.copied") : t("end.share_button")}
        </Button>
      </div>
      {token ? (
        <section className="card stack" aria-labelledby="token-title">
          <h2 id="token-title">{t("end.token_title")}</h2>
          <p className="token" data-testid="contributor-token" translate="no">
            {token}
          </p>
          <p className="small">{t("end.token_note")}</p>
          {copied === "failed" ? (
            <div className="notice notice-warn" role="status">
              <Icon name="warning" />
              <p>{t("end.copy_failed")}</p>
            </div>
          ) : null}
          <Button kind="secondary" block onClick={() => copy(token, "token")}>
            {copied === "token" ? t("end.copied") : t("end.copy_token")}
          </Button>
        </section>
      ) : null}
      {children}
    </div>
  );
}
