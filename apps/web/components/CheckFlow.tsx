"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { FormQuestion } from "./FormQuestion";
import { LocationStep } from "./LocationStep";
import { PhotoPicker, type PickedPhoto } from "./PhotoPicker";
import { Progress } from "./Progress";
import { api, ApiError, isNetworkError, type AnswerValue, type DraftRequest, type DraftResponse, type Followup, type SpotRef } from "@/lib/api";
import { content, type FormItem } from "@/lib/content";
import { enqueue, flushQueue, getQueued, onQueueChange } from "@/lib/offline";
import { clearContributorToken, getContributorToken, rememberSpot } from "@/lib/session";
import { t } from "@/lib/t";

type Stage =
  | { name: "intro" }
  | { name: "location" }
  | { name: "items"; index: number }
  | { name: "photos" }
  | { name: "sending" }
  | { name: "followups"; draft: DraftResponse; uploadedIds: string[] }
  | { name: "finalizing" }
  | { name: "done"; visit_id: string; spot_id: string }
  | { name: "queued"; id: number; status: "waiting" | "sending" | "sent" | "failed"; spot_id?: string }
  | { name: "error"; message: string; retry: () => void };

function visibleItems(answers: Record<string, AnswerValue>): FormItem[] {
  return content.form.items.filter((item) => {
    if (!item.depends_on) return true;
    return answers[item.depends_on.item] === item.depends_on.value;
  });
}

/**
 * The guided creek check from content/form.yaml: one question per screen in the form's order,
 * location first, photos welcome, follow-ups from the API shown in place, offline queue when the
 * network is down.
 */
export function CheckFlow() {
  const [stage, setStage] = useState<Stage>({ name: "intro" });
  const [spot, setSpot] = useState<SpotRef | null>(null);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [photos, setPhotos] = useState<PickedPhoto[]>([]);
  const [followupAnswers, setFollowupAnswers] = useState<Record<string, string>>({});
  const [finalRating, setFinalRating] = useState<string | null>(null);
  const [changingRating, setChangingRating] = useState(false);
  const [followupPhotos, setFollowupPhotos] = useState<Record<string, PickedPhoto[]>>({});

  const items = useMemo(() => visibleItems(answers), [answers]);
  const firstRating = typeof answers.overall_rating === "string" ? answers.overall_rating : null;
  const ratingItem = content.form.items.find((i) => i.id === "overall_rating");

  // Watch the queue while a saved check waits.
  const queuedId = stage.name === "queued" ? stage.id : null;
  useEffect(() => {
    if (queuedId === null) return;
    const id = queuedId;
    const refresh = async () => {
      const q = await getQueued(id);
      if (q) setStage({ name: "queued", id, status: q.status, spot_id: q.result?.spot_id });
    };
    const off = onQueueChange(() => void refresh());
    void refresh();
    return off;
  }, [queuedId]);

  function draftBody(photo_ids: string[]): DraftRequest {
    const token = getContributorToken();
    return {
      ...(token ? { contributor_token: token } : {}),
      spot: spot as SpotRef,
      answers,
      first_rating: firstRating,
      photo_ids,
    };
  }

  async function send() {
    setStage({ name: "sending" });
    try {
      const ids: string[] = [];
      for (const p of photos) {
        const { photo_id } = await api.upload(p.blob, p.name);
        ids.push(photo_id);
      }
      let draft: DraftResponse;
      try {
        draft = await api.checkDraft(draftBody(ids));
      } catch (err) {
        // An unknown contributor token is a 404 with a plain sentence. Drop the token and send without it.
        if (err instanceof ApiError && err.status === 404 && getContributorToken()) {
          clearContributorToken();
          draft = await api.checkDraft(draftBody(ids));
        } else throw err;
      }
      setFinalRating(firstRating);
      if (draft.followups.length === 0) {
        await finalize(draft, {}, firstRating);
      } else {
        setStage({ name: "followups", draft, uploadedIds: ids });
      }
    } catch (err) {
      if (isNetworkError(err)) {
        try {
          const id = await enqueue({ kind: "check", created_at: new Date().toISOString(), draft: draftBody([]), photos: photos.map((p) => ({ name: p.name, type: p.type, blob: p.blob })) });
          setStage({ name: "queued", id, status: "waiting" });
        } catch {
          setStage({ name: "error", message: t("error.network"), retry: () => void send() });
        }
      } else {
        setStage({ name: "error", message: t("error.server"), retry: () => void send() });
      }
    }
  }

  async function finalize(draft: DraftResponse, fAnswers: Record<string, string>, rating: string | null) {
    setStage({ name: "finalizing" });
    try {
      const merged = { ...fAnswers };
      for (const f of draft.followups) {
        if (f.kind === "photo" && (followupPhotos[f.rule_id]?.length ?? 0) > 0 && !merged[f.rule_id]) {
          const { photo_id } = await api.upload(followupPhotos[f.rule_id][0].blob, followupPhotos[f.rule_id][0].name);
          merged[f.rule_id] = photo_id;
        }
      }
      const res = await api.checkFinalize({ draft_id: draft.draft_id, followup_answers: merged, final_rating: rating });
      const spotName = spot && "new" in spot ? spot.new.name : t("check.saved_spot_default");
      rememberSpot({ spot_id: res.spot_id, name: spotName });
      setStage({ name: "done", visit_id: res.visit_id, spot_id: res.spot_id });
    } catch (err) {
      setStage({ name: "error", message: isNetworkError(err) ? t("error.network") : t("error.server"), retry: () => void finalize(draft, fAnswers, rating) });
    }
  }

  function answerItem(index: number, value: AnswerValue | undefined) {
    const item = items[index];
    const next = { ...answers };
    if (value === undefined) delete next[item.id];
    else next[item.id] = value;
    setAnswers(next);
    const nextItems = visibleItems(next);
    const pos = nextItems.findIndex((i) => i.id === item.id);
    if (pos + 1 >= nextItems.length) setStage({ name: "photos" });
    else setStage({ name: "items", index: pos + 1 });
  }

  switch (stage.name) {
    case "intro":
      return (
        <div className="stack">
          <FocusHeading>{t("check.title")}</FocusHeading>
          <p>{t("check.intro")}</p>
          <p className="small muted">{t("check.unverified_note")}</p>
          {/* The same bottom block as the test screens, so Start sits in thumb reach. */}
          <div className="actions">
            <button type="button" className="btn btn-block" onClick={() => setStage({ name: "location" })}>
              {t("check.start")}
            </button>
          </div>
        </div>
      );
    case "location":
      return (
        <LocationStep
          onNext={(s) => {
            setSpot(s);
            setStage({ name: "items", index: 0 });
          }}
          onBack={() => setStage({ name: "intro" })}
        />
      );
    case "items": {
      const item = items[stage.index];
      if (!item) {
        setStage({ name: "photos" });
        return null;
      }
      return (
        <div className="stack" key={item.id}>
          <Progress value={stage.index + 1} max={items.length} labelKey="check.progress" />
          <FormQuestion
            item={item}
            value={answers[item.id]}
            onAnswer={(v) => answerItem(stage.index, v)}
            onSkip={() => answerItem(stage.index, undefined)}
            onBack={() => (stage.index === 0 ? setStage({ name: "location" }) : setStage({ name: "items", index: stage.index - 1 }))}
          />
        </div>
      );
    }
    case "photos":
      return (
        <div className="stack">
          <FocusHeading>{t("check.photos_title")}</FocusHeading>
          <p>{t("check.photos_intro")}</p>
          <PhotoPicker photos={photos} onChange={setPhotos} />
          <div className="btn-row">
            <button type="button" className="btn btn-secondary" onClick={() => setStage({ name: "items", index: Math.max(0, items.length - 1) })}>
              {t("check.back")}
            </button>
            <button type="button" className="btn" onClick={() => void send()}>
              {t("check.send")}
            </button>
          </div>
        </div>
      );
    case "sending":
    case "finalizing":
      return (
        <p role="status" className="muted">
          {t("check.sending")}
        </p>
      );
    case "followups":
      return (
        <div className="stack">
          <FocusHeading>{t("check.followups_title")}</FocusHeading>
          <p className="small muted">{t("check.followups_intro")}</p>
          {stage.draft.followups.map((f) => (
            <FollowupCard
              key={f.rule_id}
              followup={f}
              value={followupAnswers[f.rule_id]}
              onAnswer={(v) => setFollowupAnswers((a) => ({ ...a, [f.rule_id]: v }))}
              photos={followupPhotos[f.rule_id] ?? []}
              onPhotos={(p) => setFollowupPhotos((m) => ({ ...m, [f.rule_id]: p }))}
              changingRating={changingRating}
              onChangeRating={() => setChangingRating(true)}
              ratingOptions={ratingItem?.options ?? []}
              finalRating={finalRating}
              onFinalRating={(r) => {
                setFinalRating(r);
                setChangingRating(false);
                setFollowupAnswers((a) => ({ ...a, [f.rule_id]: "change" }));
              }}
            />
          ))}
          <button type="button" className="btn btn-block" onClick={() => void finalize(stage.draft, followupAnswers, finalRating)}>
            {t("check.finish")}
          </button>
        </div>
      );
    case "done":
      return (
        <div className="stack">
          <FocusHeading>{t("check.done_title")}</FocusHeading>
          <p className="notice notice-ok" role="status">
            {t("check.done_body")}
          </p>
          <p>
            <Link className="btn btn-block" href={`/spot?id=${encodeURIComponent(stage.spot_id)}`}>
              {t("check.done_view")}
            </Link>
          </p>
          <p>{t("footer.snapshot")}</p>
        </div>
      );
    case "queued":
      return (
        <div className="stack">
          <FocusHeading>{t("check.saved_title")}</FocusHeading>
          {stage.status === "sent" ? (
            <>
              <p className="notice notice-ok" role="status" data-testid="queue-sent">
                {t("check.sent")}
              </p>
              {stage.spot_id ? (
                <p>
                  <Link className="btn btn-block" href={`/spot?id=${encodeURIComponent(stage.spot_id)}`}>
                    {t("check.done_view")}
                  </Link>
                </p>
              ) : null}
            </>
          ) : stage.status === "failed" ? (
            <p className="notice notice-bad" role="alert">
              {t("check.queue_failed")}
            </p>
          ) : (
            <>
              <p className="notice notice-warn" role="status" data-testid="queue-saved">
                {t("check.saved_offline")}
              </p>
              <div className="btn-row">
                <button type="button" className="btn btn-secondary" onClick={() => void flushQueue()}>
                  {t("check.send_now")}
                </button>
              </div>
            </>
          )}
        </div>
      );
    case "error":
      return (
        <div className="stack">
          <p className="notice notice-bad" role="alert">
            {stage.message}
          </p>
          <button type="button" className="btn" onClick={stage.retry}>
            {t("error.retry")}
          </button>
        </div>
      );
  }
}

function FollowupCard({
  followup,
  value,
  onAnswer,
  photos,
  onPhotos,
  changingRating,
  onChangeRating,
  ratingOptions,
  finalRating,
  onFinalRating,
}: {
  followup: Followup;
  value: string | undefined;
  onAnswer: (v: string) => void;
  photos: PickedPhoto[];
  onPhotos: (p: PickedPhoto[]) => void;
  changingRating: boolean;
  onChangeRating: () => void;
  ratingOptions: { id: string; label: string; value: string }[];
  finalRating: string | null;
  onFinalRating: (r: string) => void;
}) {
  return (
    <section className="card stack" aria-label={followup.rule_id}>
      <p>
        <strong>{followup.question_text}</strong>
      </p>
      {followup.kind === "yesno" ? (
        <div className="option-list">
          {[
            ["yes", t("check.yes")],
            ["no", t("check.no")],
            ["cant_tell", t("check.not_sure")],
          ].map(([v, label]) => (
            <button key={v} type="button" className="option" aria-pressed={value === v} onClick={() => onAnswer(v)}>
              {label}
            </button>
          ))}
        </div>
      ) : null}
      {followup.kind === "keep_rating" ? (
        <div className="stack">
          <div className="btn-row">
            <button type="button" className="btn" aria-pressed={value === "keep"} onClick={() => onAnswer("keep")}>
              {t("check.keep_rating")}
            </button>
            <button type="button" className="btn btn-secondary" aria-pressed={value === "change"} onClick={onChangeRating}>
              {t("check.change_rating")}
            </button>
          </div>
          {changingRating ? (
            <div className="option-list">
              {ratingOptions.map((o) => (
                <button key={o.id} type="button" className="option" aria-pressed={finalRating === o.value} onClick={() => onFinalRating(o.value)}>
                  {o.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {followup.kind === "look_again" ? (
        <div className="btn-row">
          <button type="button" className="btn" aria-pressed={value === "looked"} onClick={() => onAnswer("looked")}>
            {t("check.looked_again")}
          </button>
          <button type="button" className="btn btn-secondary" aria-pressed={value === "skipped"} onClick={() => onAnswer("skipped")}>
            {t("check.skip")}
          </button>
        </div>
      ) : null}
      {followup.kind === "photo" ? (
        <div className="stack">
          <PhotoPicker photos={photos} onChange={onPhotos} max={1} />
          <button type="button" className="btn btn-quiet" aria-pressed={value === "skipped"} onClick={() => onAnswer("skipped")}>
            {t("check.skip")}
          </button>
        </div>
      ) : null}
    </section>
  );
}
