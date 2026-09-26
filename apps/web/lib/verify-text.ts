// The words /verify shows for an OpenTimestamps proof, from results/ots.json. Pure, so
// tests/verify.spec.ts can check every status, including the ones the committed file has not
// reached yet: a proof is pending for hours before a Bitcoin block confirms it.
import { anchorFor, headsAgainstLog, proofDate, type AuditEntry, type OtsProof } from "./chain";
import { t } from "./t";

const day = (utc?: string) => utc?.slice(0, 10) ?? "";

export function proofName(p: OtsProof): string {
  if (p.what === "audit_head") return t("verify.proof.audit_head", { seq: p.audit_seq ?? "" });
  if (["prereg_tag", "analysis_plan", "prereg_tag_v2", "analysis_plan_v2"].includes(p.what ?? "")) return t(`verify.proof.${p.what}`);
  return t("verify.proof.other");
}

export function proofStatus(p: OtsProof): string {
  const height = p.bitcoin?.block_height ?? "";
  if (p.status === "confirmed") return t("verify.status.confirmed", { height, date: day(p.bitcoin?.block_time_utc) });
  if (p.status === "unchecked") return t("verify.status.unchecked", { height });
  if (p.status === "broken") return t("verify.status.broken");
  return t("verify.status.pending");
}

/**
 * The day, as "Sep 24", of the confirmed stamp that covers the whole audit log, or null when no
 * confirmed stamp covers its last line. A stamp shows each line as it was on the day of the stamp,
 * not the day it was written, so the /judges door says "no line has changed since" this day and
 * no more (CRITIC_09 Q03).
 */
export function logStampDay(entries: AuditEntry[], proofs: OtsProof[]): string | null {
  const last = entries[entries.length - 1];
  if (!last) return null;
  const p = anchorFor(last.seq, entries, headsAgainstLog(proofs, entries));
  const when = p?.status === "confirmed" ? p.bitcoin?.block_time_utc : undefined;
  if (!when) return null;
  const d = new Date(when);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

/** What a line of the audit log says about the proof that covers it, if one does. */
export function anchorText(p: OtsProof | null): string {
  if (!p) return t("verify.anchor_none");
  const height = p.bitcoin?.block_height ?? "";
  if (p.status === "confirmed") return t("verify.anchor_confirmed", { height, date: day(p.bitcoin?.block_time_utc) });
  if (p.status === "unchecked") return t("verify.anchor_unchecked", { height });
  return t("verify.anchor_pending", { date: proofDate(p) });
}
