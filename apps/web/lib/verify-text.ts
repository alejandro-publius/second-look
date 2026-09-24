// The words /verify shows for an OpenTimestamps proof, from results/ots.json. Pure, so
// tests/verify.spec.ts can check every status, including the ones the committed file has not
// reached yet: a proof is pending for hours before a Bitcoin block confirms it.
import { proofDate, type OtsProof } from "./chain";
import { t } from "./t";

const day = (utc?: string) => utc?.slice(0, 10) ?? "";

export function proofName(p: OtsProof): string {
  if (p.what === "audit_head") return t("verify.proof.audit_head", { seq: p.audit_seq ?? "" });
  if (p.what === "prereg_tag" || p.what === "analysis_plan") return t(`verify.proof.${p.what}`);
  return t("verify.proof.other");
}

export function proofStatus(p: OtsProof): string {
  const height = p.bitcoin?.block_height ?? "";
  if (p.status === "confirmed") return t("verify.status.confirmed", { height, date: day(p.bitcoin?.block_time_utc) });
  if (p.status === "unchecked") return t("verify.status.unchecked", { height });
  if (p.status === "broken") return t("verify.status.broken");
  return t("verify.status.pending");
}

/** What a line of the audit log says about the proof that covers it, if one does. */
export function anchorText(p: OtsProof | null): string {
  if (!p) return t("verify.anchor_none");
  const height = p.bitcoin?.block_height ?? "";
  if (p.status === "confirmed") return t("verify.anchor_confirmed", { height, date: day(p.bitcoin?.block_time_utc) });
  if (p.status === "unchecked") return t("verify.anchor_unchecked", { height });
  return t("verify.anchor_pending", { date: proofDate(p) });
}
