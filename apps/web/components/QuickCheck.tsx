"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import type { PickedPhoto } from "./PhotoPicker";
import { Progress } from "./Progress";
import { Button } from "./ui/Button";
import { api, ApiError, isNetworkError, type QuickColour, type QuickSmell } from "@/lib/api";
import { downsize } from "@/lib/image";
import { enqueue } from "@/lib/offline";
import { clearContributorToken, getContributorToken } from "@/lib/session";
import { t } from "@/lib/t";

type Pipe = "present" | "absent" | "cant_tell";

// The API still accepts "foam" as a colour, but foam is not a colour and the API has nowhere to
// store foam as its own answer, so the screen does not offer it.
const COLOURS: readonly (readonly [QuickColour, string])[] = [
  ["clear", "quick.colour_clear"],
  ["muddy", "quick.colour_muddy"],
  ["coloured", "quick.colour_coloured"],
  ["cant_tell", "quick.colour_cant_tell"],
];
const SMELLS: readonly (readonly [QuickSmell, string])[] = [
  ["none", "quick.smell_none"],
  ["bad", "quick.smell_bad"],
  ["cant_tell", "quick.smell_cant_tell"],
];
const PIPE: readonly (readonly [Pipe, string])[] = [
  ["present", "check.yes"],
  ["absent", "check.no"],
  ["cant_tell", "quick.pipe_cant_tell"],
];
// Colour, smell, pipe, then the photo screen with Send.
const STEPS = 4;
const PHOTO_STEP = STEPS - 1;

/** One question as a fieldset. Its legend is the screen heading, and a tap answers and moves on. */
function Question<V extends string>({ legend, options, value, onPick }: { legend: string; options: readonly (readonly [V, string])[]; value: V | null; onPick: (v: V) => void }) {
  return (
    <fieldset className="question-set">
      <legend>
        <FocusHeading>{legend}</FocusHeading>
      </legend>
      <div className="option-list">
        {options.map(([v, key]) => (
          <button key={v} type="button" className="option" aria-pressed={value === v} onClick={() => onPick(v)}>
            {t(key)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

/** One optional photo, made smaller on the phone before it is sent. */
function OnePhoto({ photo, onChange }: { photo: PickedPhoto | null; onChange: (p: PickedPhoto | null) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function picked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !file.type.startsWith("image/")) {
      if (input.current) input.current.value = "";
      return;
    }
    setBusy(true);
    try {
      const blob = await downsize(file);
      onChange({ name: file.name.replace(/\.[^.]+$/, "") + ".jpg", type: blob.type || "image/jpeg", blob, bytes: blob.size });
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div className="stack">
      <input ref={input} className="visually-hidden" type="file" accept="image/*" capture="environment" onChange={picked} aria-label={t("check.add_photo")} tabIndex={-1} />
      <p className="small muted" role="status">
        {photo ? t("quick.photo_one") : t("quick.photo_none")}
      </p>
      {photo ? (
        <Button kind="secondary" onClick={() => onChange(null)}>
          {t("quick.photo_remove")}
        </Button>
      ) : (
        <Button kind="secondary" disabled={busy} busy={busy} busyLabel={t("check.photo_working")} onClick={() => input.current?.click()}>
          {t("check.add_photo")}
        </Button>
      )}
    </div>
  );
}

/**
 * The 20 second return check for a saved spot: colour, smell, is the pipe running, then an
 * optional photo and Send. One question per screen, as in the test and the creek check.
 */
export function QuickCheck({ spotId }: { spotId: string }) {
  const [step, setStep] = useState(0);
  const [colour, setColour] = useState<QuickColour | null>(null);
  const [smell, setSmell] = useState<QuickSmell | null>(null);
  const [pipe, setPipe] = useState<Pipe | null>(null);
  const [photo, setPhoto] = useState<PickedPhoto | null>(null);
  const [state, setState] = useState<"form" | "sending" | "done" | "queued" | "error">("form");
  const [error, setError] = useState<string | null>(null);

  function answer<V>(set: (v: V) => void) {
    return (v: V) => {
      set(v);
      setError(null);
      setStep((s) => Math.min(s + 1, PHOTO_STEP));
    };
  }

  async function send() {
    if (!colour || !smell || !pipe) {
      // Every screen before this one needs a tap to leave it, so this only guards the types.
      setStep(!colour ? 0 : !smell ? 1 : 2);
      setError(t("quick.need_all"));
      return;
    }
    setError(null);
    setState("sending");
    const token = getContributorToken();
    const body = { ...(token ? { contributor_token: token } : {}), colour, smell, pipe_running: pipe };
    try {
      let photo_id: string | undefined;
      if (photo) photo_id = (await api.upload(photo.blob, photo.name)).photo_id;
      try {
        await api.quick(spotId, { ...body, ...(photo_id ? { photo_id } : {}) });
      } catch (err) {
        // An unknown contributor token is a 404 with a plain sentence. Drop it and send without.
        if (err instanceof ApiError && err.status === 404 && token) {
          clearContributorToken();
          const { contributor_token: _dropped, ...rest } = body;
          void _dropped;
          await api.quick(spotId, { ...rest, ...(photo_id ? { photo_id } : {}) });
        } else throw err;
      }
      setState("done");
    } catch (err) {
      if (isNetworkError(err)) {
        try {
          await enqueue({ kind: "quick", created_at: new Date().toISOString(), quick: { spot_id: spotId, body }, photos: photo ? [{ name: photo.name, type: photo.type, blob: photo.blob }] : [] });
          setState("queued");
          return;
        } catch {
          // fall through
        }
      }
      setError(isNetworkError(err) ? t("error.network") : t("error.server"));
      setState("error");
    }
  }

  if (state === "done" || state === "queued") {
    return (
      <div className="stack">
        <FocusHeading>{t("quick.title")}</FocusHeading>
        <p className={state === "done" ? "notice notice-ok" : "notice notice-warn"} role="status">
          {state === "done" ? t("quick.done") : t("check.saved_offline")}
        </p>
        <p>
          <Link className="btn btn-block" href={`/spot?id=${encodeURIComponent(spotId)}`}>
            {t("quick.view_record")}
          </Link>
        </p>
      </div>
    );
  }

  const sending = state === "sending";
  const back = (
    <Button kind="secondary" disabled={sending} onClick={() => setStep((s) => Math.max(0, s - 1))}>
      {t("check.back")}
    </Button>
  );

  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        void send();
      }}
    >
      <p className="small muted">{t("quick.title")}</p>
      {step === 0 ? <p className="small muted">{t("quick.intro")}</p> : null}
      {/* The count stays mounted from screen to screen, so a screen reader hears it change. Each
          screen below sits in its own slot, so moving on mounts a new heading and it takes focus. */}
      <Progress value={step + 1} max={STEPS} labelKey="quick.progress" />
      {step === 0 ? <Question legend={t("quick.colour")} options={COLOURS} value={colour} onPick={answer(setColour)} /> : null}
      {step === 1 ? <Question legend={t("quick.smell")} options={SMELLS} value={smell} onPick={answer(setSmell)} /> : null}
      {step === 2 ? <Question legend={t("quick.pipe")} options={PIPE} value={pipe} onPick={answer(setPipe)} /> : null}
      {step === PHOTO_STEP ? (
        <fieldset className="question-set">
          <legend>
            <FocusHeading>{t("quick.photo")}</FocusHeading>
          </legend>
          <OnePhoto photo={photo} onChange={setPhoto} />
        </fieldset>
      ) : null}
      {error ? (
        <p className="notice notice-warn" role="alert">
          {error}
        </p>
      ) : null}
      {step === 0 ? null : (
        <div className="actions">
          {step === PHOTO_STEP ? (
            <div className="btn-row">
              {back}
              <Button type="submit" disabled={sending} busy={sending} busyLabel={t("check.sending")}>
                {t("quick.send")}
              </Button>
            </div>
          ) : (
            back
          )}
        </div>
      )}
    </form>
  );
}
