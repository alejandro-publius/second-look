"use client";

import { useRef, useState } from "react";
import { downsize } from "@/lib/image";
import { t } from "@/lib/t";

export interface PickedPhoto {
  name: string;
  type: string;
  blob: Blob;
  bytes: number;
}

/** Picks photos from the camera or the library and downsizes them on the phone before upload. */
export function PhotoPicker({ photos, onChange, max = 4, capture = true }: { photos: PickedPhoto[]; onChange: (p: PickedPhoto[]) => void; max?: number; capture?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function picked(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;
    setBusy(true);
    try {
      const next = photos.slice();
      for (const f of files) {
        if (next.length >= max) break;
        if (!f.type.startsWith("image/")) continue;
        const blob = await downsize(f);
        next.push({ name: f.name.replace(/\.[^.]+$/, "") + ".jpg", type: blob.type || "image/jpeg", blob, bytes: blob.size });
      }
      onChange(next);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div className="stack">
      <input
        ref={input}
        className="visually-hidden"
        id="photo-input"
        type="file"
        accept="image/*"
        multiple={max > 1}
        capture={capture ? "environment" : undefined}
        onChange={picked}
        aria-label={t("check.add_photo")}
        tabIndex={-1}
      />
      <div className="btn-row">
        <button type="button" className="btn btn-secondary" disabled={busy || photos.length >= max} onClick={() => input.current?.click()}>
          {busy ? t("check.photo_working") : t("check.add_photo")}
        </button>
      </div>
      <p className="small muted" role="status">
        {photos.length === 1 ? t("check.photo_count_one") : t("check.photo_count", { n: photos.length })}
      </p>
      {photos.length > 0 ? (
        <ul className="stack">
          {photos.map((p, i) => (
            <li key={`${p.name}-${i}`} className="small">
              {p.name} ({Math.round(p.bytes / 1024)} kB){" "}
              <button type="button" className="btn btn-quiet" onClick={() => onChange(photos.filter((_, j) => j !== i))}>
                {t("check.photo_remove")}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
