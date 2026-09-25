// A finished video walk's demo record on the Worker (UPDATE_30 section 1 item 3). A port of
// apps/api/walk_store.py. The phone sends the walk's answers once it is finished; this checks
// them against the form, builds the record with core/walks.ts walkRecord (proved equal to Python
// by golden vectors) and keeps it in its own table, walk_record, so a link to it opens on any
// device.
//
// A walk record is a demo. It lives in walk_record only, never in spot, visit or fhir_bundle, so
// nothing that counts, maps or mirrors creek checks can see it: not the study counts, not a real
// creek's city view, not the sandbox mirror. Every resource in its Bundle carries the demo tag.
//
// The guards: the body is at most WALK_MAX_BYTES and holds the walk id, the answers, the time and
// the follow-up answers with the final rating only, each answer a value from the form's own lists;
// at most WALK_DAILY_CAP records a day on the whole server; each record is deleted WALK_KEEP_DAYS
// days after it is stored, by the daily purge and by every new store, and is never served after
// that date.
//
// The follow-ups (judge walk W01): the store runs the creek check's own rules on the answers
// (core/walks.ts walkFollowups), so it, not the phone, decides which questions were asked, checks
// each answer against its question (walkChecks), and keeps the checks that ran and the final
// rating in walk_checks, one row per record, deleted with it. A body with neither follow-up field
// was sent before walks asked any, so it keeps no checks.

import CONTENT from "./content.json";
import { Invalid, NotFound, questionText, validateAnswers, validateRating } from "./check";
import { FORM_ITEMS, checkBundle } from "./core/fhir_emit";
import type { AnswerValue, CheckResult } from "./core/types";
import { WALK_DAILY_CAP, WALK_KEEP_DAYS, WALK_MAX_BYTES, WalkRecordError, walkChecks, walkFollowups, walkRecord, type WalkRef } from "./core/walks";
import { TooLarge } from "./uploads";

/** The same walk id and time with other answers: two people finished one clip in one second. */
export class Conflict extends Error {}
/** The daily cap on stored walk records is reached. */
export class TooMany extends Error {}

const WALKS: Map<string, WalkRef> = new Map(CONTENT.walks.map((w) => [w.id, { id: w.id, spot_name: w.spot_name, creek_name: w.creek_name }]));
const BODY_KEYS = new Set(["walk_id", "answers", "answered_at", "followup_answers", "final_rating"]);
const RECORD_ID_RE = /^walk-[0-9a-f]{16}$/;

interface WalkRow {
  record_id: string;
  walk_id: string;
  answered_at: string;
  answers_json: string;
  bundle_json: string;
  created_at: string;
  delete_after: string;
}

/** The answers as one string with the keys in order, so the same walk sent twice compares equal. */
function answersText(answers: Record<string, unknown>): string {
  return JSON.stringify(Object.fromEntries(Object.keys(answers).sort().map((k) => [k, answers[k]])));
}

function stored(row: Pick<WalkRow, "record_id" | "walk_id" | "answered_at" | "delete_after">) {
  return { record_id: row.record_id, walk_id: row.walk_id, answered_at: row.answered_at, delete_after: row.delete_after };
}

interface ChecksRow {
  final_rating: string | null;
  checks_json: string;
}

/** The checks a walk ran and its final rating, as the store keeps them. */
interface WalkKept {
  checks: CheckResult[];
  final_rating: string | null;
}

/** Deletes every walk record past its date, with its checks. Returns how many records went. */
export async function purgeWalks(db: D1Database, now: string): Promise<number> {
  const [, records] = await db.batch([
    db.prepare("DELETE FROM walk_checks WHERE record_id IN (SELECT record_id FROM walk_record WHERE delete_after <= ?)").bind(now),
    db.prepare("DELETE FROM walk_record WHERE delete_after <= ?").bind(now),
  ]);
  return Number(records.meta.changes ?? 0);
}

/** The follow-ups the answers call for, checked against what the phone says was answered. Null
 *  for a body with neither follow-up field: it was sent before walks asked any. */
function followupsOf(body: Record<string, unknown>, answers: Record<string, AnswerValue>): WalkKept | null {
  if (!("followup_answers" in body) && !("final_rating" in body)) return null;
  const given = body.followup_answers ?? {};
  if (given === null || typeof given !== "object" || Array.isArray(given)) throw new Invalid("followup_answers must be an object of follow-up ids and answers.");
  const finalRating = validateRating(body.final_rating);
  const chosen = walkFollowups(answers, CONTENT.followups, FORM_ITEMS);
  try {
    return walkChecks(answers, chosen, chosen.map(questionText), given as Record<string, unknown>, finalRating);
  } catch (err) {
    if (err instanceof WalkRecordError) throw new Invalid(err.message);
    throw err;
  }
}

/** What GET gives for a walk's checks: none, and its own rating, for a walk stored without them. */
function keptOf(row: ChecksRow | null, answers: Record<string, unknown>) {
  const first = typeof answers.overall_rating === "string" ? answers.overall_rating : null;
  if (row === null) return { checks: [] as CheckResult[], first_rating: first, final_rating: first };
  return { checks: JSON.parse(row.checks_json) as CheckResult[], first_rating: first, final_rating: row.final_rating };
}

async function readBody(request: Request): Promise<Record<string, unknown>> {
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (declared > WALK_MAX_BYTES) throw new TooLarge("That walk is too large to store.");
  const raw = new Uint8Array(await request.arrayBuffer());
  if (raw.length > WALK_MAX_BYTES) throw new TooLarge("That walk is too large to store.");
  let body: unknown;
  try {
    body = JSON.parse(new TextDecoder().decode(raw));
  } catch {
    throw new Invalid("That was not JSON.");
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new Invalid("Send the walk as one JSON object.");
  for (const key of Object.keys(body)) if (!BODY_KEYS.has(key)) throw new Invalid(`A walk has no field called '${key}'.`);
  return body as Record<string, unknown>;
}

/** POST /api/walk: stores a finished walk's record and returns its id. The same walk sent again,
 *  as the phone's queue may, returns the same id and stores nothing new. */
export async function storeWalk(db: D1Database, request: Request, now: string) {
  const body = await readBody(request);
  const walk = typeof body.walk_id === "string" ? WALKS.get(body.walk_id) : undefined;
  if (walk === undefined) throw new NotFound("We do not know that walk.");
  if (!body.answers || typeof body.answers !== "object" || Array.isArray(body.answers)) throw new Invalid("answers must be an object of question ids and answers.");
  const answers = validateAnswers(body.answers as Record<string, unknown>);
  let row;
  try {
    row = walkRecord(walk, answers, body.answered_at, now);
  } catch (err) {
    if (err instanceof WalkRecordError) throw new Invalid(err.message);
    throw err;
  }
  if (checkBundle(row.bundle as never).length > 0) throw new Invalid("That walk would make a record with a broken link inside it.");
  const kept = followupsOf(body, answers);
  const text = answersText(answers);
  const keptText = kept === null ? null : JSON.stringify(kept.checks);
  await purgeWalks(db, now);
  const same = async () => {
    const existing = await db.prepare("SELECT * FROM walk_record WHERE record_id = ?").bind(row.record_id).first<WalkRow>();
    if (existing === null) return null;
    if (existing.walk_id === row.walk_id && existing.answers_json === text) {
      // The same walk sent again from the queue carries the same follow-up answers. A record kept
      // with none, from before walks asked any, is the same walk whatever this one carries.
      const was = await db.prepare("SELECT final_rating, checks_json FROM walk_checks WHERE record_id = ?").bind(row.record_id).first<ChecksRow>();
      if (kept === null || was === null || (was.checks_json === keptText && was.final_rating === kept.final_rating)) return stored(existing);
    }
    throw new Conflict("Another walk of this clip was stored in the same second. Start again and finish it once more.");
  };
  const earlier = await same();
  if (earlier !== null) return earlier;
  // One statement, so two walks arriving together cannot both take the last place of the day. The
  // checks go in the same batch, so a record is never kept without the checks it ran.
  const dayStart = `${now.slice(0, 10)}T00:00:00Z`;
  const statements = [
    db
      .prepare(
        `INSERT OR IGNORE INTO walk_record (record_id, walk_id, answered_at, answers_json, bundle_json, created_at, delete_after)
         SELECT ?, ?, ?, ?, ?, ?, ? WHERE (SELECT COUNT(*) FROM walk_record WHERE created_at >= ?) < ?`,
      )
      .bind(row.record_id, row.walk_id, row.answered_at, text, JSON.stringify(row.bundle), row.created_at, row.delete_after, dayStart, WALK_DAILY_CAP),
  ];
  if (kept !== null) {
    statements.push(
      db
        .prepare(
          `INSERT OR IGNORE INTO walk_checks (record_id, final_rating, checks_json)
           SELECT ?, ?, ? WHERE EXISTS (SELECT 1 FROM walk_record WHERE record_id = ? AND answers_json = ?)`,
        )
        .bind(row.record_id, kept.final_rating, keptText, row.record_id, text),
    );
  }
  const [inserted] = await db.batch(statements);
  if (!inserted.meta.changes) {
    const raced = await same();
    if (raced !== null) return raced;
    throw new TooMany("The demo store has taken all the walks it can for today. Your record is still on this page; try again tomorrow.");
  }
  return stored(row);
}

/** GET /api/walk/{record_id}: one stored walk record, until its delete date, with the checks it
 *  ran and its first and final rating, as a creek check's visit gives them on /api/spot. */
export async function walkView(db: D1Database, recordId: string, now: string) {
  const gone = `We have no stored walk record called '${recordId.slice(0, 40)}'. A walk record is deleted ${WALK_KEEP_DAYS} days after it is stored.`;
  if (!RECORD_ID_RE.test(recordId)) throw new NotFound(gone);
  const row = await db.prepare("SELECT * FROM walk_record WHERE record_id = ? AND delete_after > ?").bind(recordId, now).first<WalkRow>();
  if (row === null) throw new NotFound(gone);
  const checks = await db.prepare("SELECT final_rating, checks_json FROM walk_checks WHERE record_id = ?").bind(recordId).first<ChecksRow>();
  const answers = JSON.parse(row.answers_json) as Record<string, unknown>;
  return { ...stored(row), answers, bundle: JSON.parse(row.bundle_json) as Record<string, unknown>, ...keptOf(checks, answers) };
}
