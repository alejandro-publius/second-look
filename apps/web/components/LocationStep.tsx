"use client";

import { useState } from "react";
import { FocusHeading } from "./FocusHeading";
import type { SpotRef } from "@/lib/api";
import { savedSpots } from "@/lib/session";
import { t } from "@/lib/t";

type Mode = "ask" | "found" | "pin";

/**
 * Where the check happens. Asks for location permission; when denied or unavailable, offers a plain
 * coordinates pin or a saved spot. No map tiles: a tile server would be a third-party origin.
 * GPS positions are rounded to two decimals (about 1 km) and marked coarse. A pin a person places
 * is sent as typed and marked exact.
 */
export function LocationStep({ onNext, onBack }: { onNext: (spot: SpotRef) => void; onBack?: () => void }) {
  const [mode, setMode] = useState<Mode>("ask");
  const [status, setStatus] = useState<string | null>(null);
  const [coords, setCoords] = useState<{ lat: number; lon: number; coarse: boolean } | null>(null);
  const [name, setName] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [error, setError] = useState<string | null>(null);
  const saved = savedSpots();

  function useMyLocation() {
    setError(null);
    if (!("geolocation" in navigator)) {
      setStatus(t("check.location_unavailable"));
      setMode("pin");
      return;
    }
    setStatus(t("check.location_asking"));
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const round = (v: number) => Math.round(v * 100) / 100;
        setCoords({ lat: round(pos.coords.latitude), lon: round(pos.coords.longitude), coarse: true });
        setStatus(t("check.location_found"));
        setMode("found");
      },
      () => {
        setStatus(t("check.location_denied"));
        setMode("pin");
      },
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 },
    );
  }

  function submitNew(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    let point = coords;
    if (mode === "pin") {
      const la = Number(lat);
      const lo = Number(lon);
      if (lat.trim() === "" || lon.trim() === "" || !Number.isFinite(la) || !Number.isFinite(lo) || la < -90 || la > 90 || lo < -180 || lo > 180) {
        setError(t("check.pin_invalid"));
        return;
      }
      point = { lat: la, lon: lo, coarse: false };
    }
    if (!point) {
      setError(t("check.location_needed"));
      return;
    }
    const trimmed = name.trim();
    if (!trimmed) {
      setError(t("check.pin_name_needed"));
      return;
    }
    onNext({ new: { name: trimmed, latitude: point.lat, longitude: point.lon, coarse: point.coarse } });
  }

  return (
    <div className="stack">
      <FocusHeading>{t("check.location_title")}</FocusHeading>
      <p>{t("check.location_intro")}</p>
      {saved.length > 0 ? (
        <section className="card stack" aria-labelledby="saved-title">
          <h2 id="saved-title">{t("check.saved_spots")}</h2>
          <div className="option-list">
            {saved.map((s) => (
              <button key={s.spot_id} type="button" className="option" onClick={() => onNext({ spot_id: s.spot_id })}>
                {s.name}
              </button>
            ))}
          </div>
        </section>
      ) : null}
      <div className="btn-row">
        <button type="button" className="btn" onClick={useMyLocation}>
          {t("check.location_use")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => setMode("pin")}>
          {t("check.pin_instead")}
        </button>
      </div>
      {status ? (
        <p className="notice" role="status">
          {status}
        </p>
      ) : null}
      {mode !== "ask" ? (
        <form className="card stack" onSubmit={submitNew} noValidate>
          {mode === "pin" ? (
            <>
              <p className="small muted">{t("check.map_note")}</p>
              <label className="field">
                <span className="field-label">{t("check.pin_lat")}</span>
                <input className="text-input" type="number" inputMode="decimal" step="any" min={-90} max={90} value={lat} onChange={(e) => setLat(e.target.value)} name="latitude" />
              </label>
              <label className="field">
                <span className="field-label">{t("check.pin_lon")}</span>
                <input className="text-input" type="number" inputMode="decimal" step="any" min={-180} max={180} value={lon} onChange={(e) => setLon(e.target.value)} name="longitude" />
              </label>
            </>
          ) : coords ? (
            <p className="small muted">{t("check.location_coarse", { lat: coords.lat, lon: coords.lon })}</p>
          ) : null}
          <label className="field">
            <span className="field-label">{t("check.pin_name")}</span>
            <input className="text-input" type="text" value={name} onChange={(e) => setName(e.target.value)} name="spot_name" autoComplete="off" maxLength={80} />
          </label>
          {error ? (
            <p className="notice notice-warn" role="alert">
              {error}
            </p>
          ) : null}
          <div className="btn-row">
            {onBack ? (
              <button type="button" className="btn btn-secondary" onClick={onBack}>
                {t("check.back")}
              </button>
            ) : null}
            <button type="submit" className="btn">
              {t("check.next")}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
