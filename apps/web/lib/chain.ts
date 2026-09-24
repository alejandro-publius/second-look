// The audit log's chain rule, the same as scripts/audit_log.py verify(): line n has seq n, a kind
// we write, the previous line's hash as its prev_hash (64 zeros for the first), and a hash that is
// the SHA-256 of "seq|ts_utc|kind|payload_sha256|prev_hash". Pure, and Web Crypto only, so it runs
// in the browser on /verify, at build time in Node, and in tests/verify.spec.ts.
// It is a hash-chained audit log, not a blockchain.

export interface AuditEntry {
  seq: number;
  ts_utc: string;
  kind: string;
  payload_sha256: string;
  prev_hash: string;
  hash: string;
}

export const GENESIS = "0".repeat(64);

/** scripts/audit_log.py KINDS. A kind outside it is a break, as verify_audit.py says. */
export const KINDS = ["plan_tagged", "key_frozen", "launch_wipe", "model_pass_table", "data_lock", "record_written", "sandbox_push"] as const;

export type ChainBreak = "seq" | "kind" | "prev" | "hash";
export type ChainResult = { ok: true; length: number; last: string } | { ok: false; line: number; reason: ChainBreak };

export function hashedText(e: AuditEntry): string {
  return `${e.seq}|${e.ts_utc}|${e.kind}|${e.payload_sha256}|${e.prev_hash}`;
}

export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Walks the chain and stops at the first break, naming its line (1 based) and why. */
export async function verifyChain(entries: AuditEntry[]): Promise<ChainResult> {
  let prev = GENESIS;
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    const line = i + 1;
    if (e.seq !== line) return { ok: false, line, reason: "seq" };
    if (!(KINDS as readonly string[]).includes(e.kind)) return { ok: false, line, reason: "kind" };
    if (e.prev_hash !== prev) return { ok: false, line, reason: "prev" };
    if ((await sha256Hex(hashedText(e))) !== e.hash) return { ok: false, line, reason: "hash" };
    prev = e.hash;
  }
  return { ok: true, length: entries.length, last: prev };
}

/** The lines of audit/log.jsonl, as scripts/audit_log.py reads them: blank lines skipped. */
export function parseLog(text: string): AuditEntry[] {
  return text
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l) as AuditEntry);
}

/** One OpenTimestamps proof as scripts/ots_status.py writes it to results/ots.json. */
export interface OtsProof {
  proof: string;
  file?: string;
  what?: "prereg_tag" | "analysis_plan" | "audit_head" | "other";
  file_sha256?: string;
  status: "pending" | "confirmed" | "unchecked" | "broken";
  bitcoin?: { block_height: number; block_time_utc?: string } | null;
  audit_seq?: number;
}

/**
 * The audit head proof that covers a line, best first: a proof of line k's hash covers every line
 * up to k, because each hash takes in the one before it. It counts only when the stamped hash is
 * the hash the chain has at that line, so a proof of some other log covers nothing here.
 */
export function anchorFor(seq: number, entries: AuditEntry[], proofs: OtsProof[]): OtsProof | null {
  const rank = { confirmed: 0, unchecked: 1, pending: 2, broken: 3 } as const;
  const covering = proofs.filter(
    (p) =>
      p.what === "audit_head" &&
      p.status !== "broken" &&
      typeof p.audit_seq === "number" &&
      p.audit_seq >= seq &&
      stampedLineHolds(p, entries),
  );
  covering.sort(
    (a, b) =>
      rank[a.status] - rank[b.status] ||
      (a.bitcoin?.block_height ?? Infinity) - (b.bitcoin?.block_height ?? Infinity) ||
      a.proof.localeCompare(b.proof),
  );
  return covering[0] ?? null;
}

/** True when this log still has, at the proof's line, the hash the proof stamped. */
export function stampedLineHolds(p: OtsProof, entries: AuditEntry[]): boolean {
  return typeof p.audit_seq === "number" && entries[p.audit_seq - 1]?.hash === p.file_sha256;
}

/**
 * The audit head proofs as /verify shows them. A proof of a line this log no longer has counts
 * as broken: the log was changed after the stamp. results/ots.json can be older than the log,
 * and a rewritten log with fresh hashes still passes verifyChain, so the page checks this itself,
 * by the rule scripts/ots_status.py uses.
 */
export function headsAgainstLog(proofs: OtsProof[], entries: AuditEntry[]): OtsProof[] {
  return proofs.filter((p) => p.what === "audit_head").map((p) => (stampedLineHolds(p, entries) ? p : { ...p, status: "broken" as const }));
}

/** The date in an audit head proof's name, proofs/audit-head-2026-09-24.ots. */
export function proofDate(p: OtsProof): string {
  return p.proof.match(/(\d{4}-\d{2}-\d{2})\.ots$/)?.[1] ?? "";
}
