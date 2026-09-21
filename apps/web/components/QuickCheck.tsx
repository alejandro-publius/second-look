"use client";

import Link from "next/link";
import { useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { PhotoPicker, type PickedPhoto } from "./PhotoPicker";
import { api, ApiError, isNetworkError, type QuickColour, type QuickSmell } from "@/lib/api";
import { enqueue } from "@/lib/offline";
import { clearContributorToken, getContributorToken } from "@/lib/session";
import { t } from "@/lib/t";

const COLOURS: QuickColour[] = ["clear", "muddy", "foam", "coloured", "cant_tell"];
const SMELLS: QuickSmell[] = ["none", "bad", "cant_tell"];
const PIPE = [
  ["present", "check.yes"],
  ["absent", "check.no"],
  ["cant_tell", "check.not_sure"],
] as const;

/** The 20 second return check for a saved spot: colour, smell, is the pipe running, optional photo. */
export function QuickCheck({ spotId }: { spotId: string }) {
  const [colour, setColour] = useState<QuickColour | null>(null);
  const [smell, setSmell] = useState<QuickSmell | null>(null);
  const [pipe, setPipe] = useState<"present" | "absent" | "cant_tell" | null>(null);
  const [photos, setPhotos] = useState<PickedPhoto[]>([]);
  const [state, setState] = useState<"form" | "sending" | "done" | "queued" | "error">("form");
  const [error, setError] = useState<string | null>(null);

  async function send() {
    if (!colour || !smell || !pipe) {
      setError(t("quick.need_all"));
      return;
    }
    setError(null);
    setState("sending");
    const token = getContributorToken();
    const body = { ...(token ? { contributor_token: token } : {}), colour, smell, pipe_running: pipe };
    try {
      let photo_id: string | undefined;
      if (photos[0]) photo_id = (await api.upload(photos[0].blob, photos[0].name)).photo_id;
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
          await enqueue({ kind: "quick", created_at: new Date().toISOString(), quick: { spot_id: spotId, body }, photos: photos.map((p) => ({ name: p.name, type: p.type, blob: p.blob })) });
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
          <Link className="btn btn-block" href={`/spot/${encodeURIComponent(spotId)}`}>
            {t("quick.view_record")}
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        void send();
      }}
    >
      <FocusHeading>{t("quick.title")}</FocusHeading>
      <p className="muted small">{t("quick.intro")}</p>
      <fieldset className="card">
        <legend>{t("quick.colour")}</legend>
        <div className="option-list">
          {COLOURS.map((c) => (
            <button key={c} type="button" className="option" aria-pressed={colour === c} onClick={() => setColour(c)}>
              {t(`quick.colour_${c}`)}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset className="card">
        <legend>{t("quick.smell")}</legend>
        <div className="option-list">
          {SMELLS.map((s) => (
            <button key={s} type="button" className="option" aria-pressed={smell === s} onClick={() => setSmell(s)}>
              {t(`quick.smell_${s}`)}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset className="card">
        <legend>{t("quick.pipe")}</legend>
        <div className="option-list">
          {PIPE.map(([v, key]) => (
            <button key={v} type="button" className="option" aria-pressed={pipe === v} onClick={() => setPipe(v)}>
              {t(key)}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset className="card">
        <legend>{t("quick.photo")}</legend>
        <PhotoPicker photos={photos} onChange={setPhotos} max={1} />
      </fieldset>
      {error ? (
        <p className="notice notice-warn" role="alert">
          {error}
        </p>
      ) : null}
      <button type="submit" className="btn btn-block" disabled={state === "sending"}>
        {state === "sending" ? t("check.sending") : t("quick.send")}
      </button>
    </form>
  );
}
