// Build time only: /verify reads the audit log and the OpenTimestamps status from the repository
// when the static page is built, so the page shows exactly what is committed. Imported by
// app/verify/page.tsx, a server component; nothing here reaches the browser but the data.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseLog, type AuditEntry, type OtsProof } from "./chain";

// next build and next dev run in apps/web, so the repository root is two folders up.
const REPO = join(process.cwd(), "..", "..");

export interface OtsStatus {
  checked_utc: string;
  proofs: OtsProof[];
}

export function auditEntries(): AuditEntry[] {
  const path = join(REPO, "audit", "log.jsonl");
  return existsSync(path) ? parseLog(readFileSync(path, "utf8")) : [];
}

export function otsStatus(): OtsStatus {
  const path = join(REPO, "results", "ots.json");
  if (!existsSync(path)) return { checked_utc: "", proofs: [] };
  const doc = JSON.parse(readFileSync(path, "utf8")) as Partial<OtsStatus>;
  return { checked_utc: doc.checked_utc ?? "", proofs: doc.proofs ?? [] };
}
