// Part 2, the assisted second look (UPDATE_31, docs/analysis_plan_v2.md). Eight more photos after
// part 1's score screen. The server alone knows the committed flags (results/assist_flags.json
// through worker/src/content.json) and answers each first answer with whether to ask; the browser
// never learns which way a flag points. No model is called here.
//
// Randomization is not reimplemented: scripts/seed_part2_arms.py writes core/allocator.py's
// sequence for each part 1 arm into part2_slot, and this only takes the next slot of the stratum.

import CONTENT from "./content.json";
import { ANSWERS, AssistError, questionNeeded, settle, sideAnswer } from "./core/assist";

export interface Part2Env {
  DB: D1Database;
}

type Reply = { status: number; body: Record<string, unknown> };
const ok = (body: Record<string, unknown>): Reply => ({ status: 200, body });
const no = (status: number, detail: string): Reply => ({ status, body: { detail } });

const ITEMS: { id: string; feature: string; gold: string }[] = CONTENT.part2_items;
const FLAGS: Record<string, string | null> = CONTENT.part2_flags as Record<string, string | null>;
const GOLD: Record<string, string> = Object.fromEntries(ITEMS.map((i) => [i.id, i.gold]));
export const PART2_ITEM_IDS = ITEMS.map((i) => i.id);
export const PART2_ARMS = ["unassisted", "assisted"];
const STRATA = ["untrained", "trained"];
const UNKNOWN = "We do not know that second look. Start it again from your score screen.";

const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
const isRight = (answer: string, gold: string) => answer === sideAnswer(gold);

function randomHex(bytes: number): string {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}

function shuffled<T>(items: T[]): T[] {
  const out = items.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const r = new Uint32Array(1);
    crypto.getRandomValues(r);
    const j = r[0] % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

interface Part2Row {
  id: string;
  session_id: string;
  arm: string | null;
  item_order: string | null;
  declined: number;
  completed_at: string | null;
}

async function part2For(env: Part2Env, part2Id: string): Promise<Part2Row | null> {
  return env.DB.prepare("SELECT id, session_id, arm, item_order, declined, completed_at FROM part2_session WHERE id = ?")
    .bind(part2Id)
    .first<Part2Row>();
}

/** Where a started part 2 stands: what is settled, what waits for Keep or Change. */
async function state(env: Part2Env, row: Part2Row): Promise<Record<string, unknown>> {
  const rows = await env.DB.prepare(
    "SELECT item_id, final_answer, question_shown FROM part2_response WHERE part2_id = ? ORDER BY position",
  )
    .bind(row.id)
    .all<{ item_id: string; final_answer: string | null; question_shown: number }>();
  const all = rows.results ?? [];
  const out: Record<string, unknown> = {
    part2_id: row.id,
    arm: row.arm,
    item_order: row.item_order ? JSON.parse(row.item_order) : [],
    answered: all.filter((r) => r.final_answer !== null).map((r) => r.item_id),
    pending: all.find((r) => r.final_answer === null)?.item_id ?? null,
    completed: row.completed_at !== null,
    total: ITEMS.length,
  };
  if (row.completed_at !== null) out.correct_total = all.filter((r) => r.final_answer !== null && isRight(r.final_answer, GOLD[r.item_id])).length;
  return out;
}

/** The offer on part 1's score screen: start (randomize once) or decline (recorded). */
export async function offer(env: Part2Env, body: Record<string, unknown>, qa: boolean): Promise<Reply> {
  const sessionId = String(body.session_id ?? "");
  const decision = body.decision === "decline" ? "decline" : body.decision === "start" ? "start" : null;
  if (decision === null) return no(422, "Choose to start the second look or to skip it.");
  const part1 = await env.DB.prepare("SELECT arm, is_test, completed_at, client_token_hash FROM session WHERE id = ?")
    .bind(sessionId)
    .first<{ arm: string; is_test: number; completed_at: string | null; client_token_hash: string }>();
  if (part1 === null) return no(404, "We do not know that session. Start again from the first screen.");
  // Part 2 opens only after part 1's score screen (UPDATE_31 section 3).
  if (part1.completed_at === null) return no(409, "The second look opens after the score screen of the first test.");

  const existing = await env.DB.prepare(
    "SELECT id, session_id, arm, item_order, declined, completed_at FROM part2_session WHERE session_id = ?",
  )
    .bind(sessionId)
    .first<Part2Row>();
  if (existing !== null && (existing.declined === 0 || decision === "decline")) {
    return ok(existing.declined ? { declined: true } : await state(env, existing));
  }
  const at = nowIso();
  const isTest = part1.is_test === 1 || qa ? 1 : 0;
  const postLock = Date.now() >= Date.parse("2026-09-28T01:00:00Z") ? 1 : 0;
  if (decision === "decline") {
    await env.DB.prepare(
      `INSERT OR IGNORE INTO part2_session (id, session_id, part1_arm, offered_at, declined, client_token_hash, is_test, post_lock)
       VALUES (?, ?, ?, ?, 1, ?, ?, ?)`,
    )
      .bind(randomHex(16), sessionId, part1.arm, at, part1.client_token_hash, isTest, postLock)
      .run();
    return ok({ declined: true });
  }

  const stratum = STRATA.includes(part1.arm) ? part1.arm : "untrained";
  const taken = await env.DB.prepare(
    "UPDATE part2_counter SET next_position = next_position + 1 WHERE stratum = ? RETURNING next_position",
  )
    .bind(stratum)
    .first<{ next_position: number }>();
  if (taken === null) return no(500, "The randomization counter for the second look is missing.");
  const slot = await env.DB.prepare("SELECT arm, block_id FROM part2_slot WHERE stratum = ? AND position = ?")
    .bind(stratum, Number(taken.next_position) - 1)
    .first<{ arm: string; block_id: number }>();
  if (slot === null) return no(500, "The randomization sequence for the second look has run out.");
  const arm = slot.arm;
  const order = shuffled(PART2_ITEM_IDS);
  const id = existing?.id ?? randomHex(16);
  if (existing !== null) {
    // Declined first, started later: the decline stays in offered_at, the start is what counts.
    await env.DB.prepare(
      "UPDATE part2_session SET declined = 0, arm = ?, block_id = ?, item_order = ?, started_at = ? WHERE id = ? AND declined = 1",
    )
      .bind(arm, slot.block_id, JSON.stringify(order), at, id)
      .run();
  } else {
    await env.DB.prepare(
      `INSERT INTO part2_session (id, session_id, part1_arm, arm, block_id, item_order, offered_at, declined,
         started_at, client_token_hash, is_test, post_lock)
       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)`,
    )
      .bind(id, sessionId, part1.arm, arm, slot.block_id, JSON.stringify(order), at, at, part1.client_token_hash, isTest, postLock)
      .run();
  }
  const row = await part2For(env, id);
  return ok(row ? await state(env, row) : { part2_id: id, arm, item_order: order });
}

/** A first answer. The reply says only whether to ask. */
export async function answer(env: Part2Env, body: Record<string, unknown>): Promise<Reply> {
  const part2Id = String(body.part2_id ?? "");
  const itemId = String(body.item_id ?? "");
  const first = String(body.answer ?? "");
  if (!ANSWERS.includes(first)) return no(422, "We do not know that answer.");
  if (!(itemId in GOLD)) return no(404, "We do not know that photo.");
  const row = await part2For(env, part2Id);
  if (row === null || row.declined) return no(404, UNKNOWN);
  const existing = await env.DB.prepare(
    "SELECT first_answer, question_shown FROM part2_response WHERE part2_id = ? AND item_id = ?",
  )
    .bind(part2Id, itemId)
    .first<{ first_answer: string; question_shown: number }>();
  if (existing !== null) {
    if (existing.first_answer !== first) return no(409, "This photo already has an answer. The first answer stays.");
    return ok({ ask: existing.question_shown === 1 });
  }
  const ask = questionNeeded(row.arm, FLAGS[itemId] ?? null, first);
  const t = Number(body.t_first_ms ?? 0);
  const settled = ask ? null : settle(first, false);
  await env.DB.prepare(
    `INSERT OR IGNORE INTO part2_response (part2_id, item_id, position, first_answer, final_answer, question_shown,
       choice, t_first_ms, t_final_ms, received_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(part2Id, itemId, Number(body.position ?? 0), first, settled?.final_answer ?? null, ask ? 1 : 0, "", t, ask ? null : t, nowIso())
    .run();
  return ok({ ask });
}

/** Keep or Change, after the question. The person's pick is what is stored. */
export async function choice(env: Part2Env, body: Record<string, unknown>): Promise<Reply> {
  const part2Id = String(body.part2_id ?? "");
  const itemId = String(body.item_id ?? "");
  const row = await env.DB.prepare(
    "SELECT first_answer, final_answer, question_shown, choice FROM part2_response WHERE part2_id = ? AND item_id = ?",
  )
    .bind(part2Id, itemId)
    .first<{ first_answer: string; final_answer: string | null; question_shown: number; choice: string }>();
  if (row === null) return no(404, "That photo has no first answer yet.");
  if (row.question_shown !== 1) return no(409, "No question was asked for this photo, so there is nothing to choose.");
  let got;
  try {
    got = settle(row.first_answer, true, body.choice ?? null, body.changed_to ?? null);
  } catch (e) {
    if (e instanceof AssistError) return no(422, e.message);
    throw e;
  }
  if (row.final_answer !== null) {
    if (row.final_answer === got.final_answer && row.choice === got.choice) return ok({ ok: true });
    return no(409, "This photo already has a final answer. The first one stays.");
  }
  await env.DB.prepare(
    "UPDATE part2_response SET final_answer = ?, choice = ?, t_final_ms = ? WHERE part2_id = ? AND item_id = ? AND final_answer IS NULL",
  )
    .bind(got.final_answer, got.choice, Number(body.t_final_ms ?? 0), part2Id, itemId)
    .run();
  return ok({ ok: true });
}

/** The end: the eight-item score once every answer is held, or the ids to send again. */
export async function complete(env: Part2Env, body: Record<string, unknown>): Promise<Reply> {
  const part2Id = String(body.part2_id ?? "");
  const row = await part2For(env, part2Id);
  if (row === null || row.declined) return no(404, UNKNOWN);
  const held = await env.DB.prepare("SELECT item_id, final_answer FROM part2_response WHERE part2_id = ?")
    .bind(part2Id)
    .all<{ item_id: string; final_answer: string | null }>();
  const settledIds = new Set((held.results ?? []).filter((r) => r.final_answer !== null).map((r) => r.item_id));
  const gap = PART2_ITEM_IDS.filter((id) => !settledIds.has(id));
  const answeredCount = Number(body.answered_count ?? 0);
  if (gap.length > 0 && body.final !== true && row.completed_at === null && answeredCount > settledIds.size) {
    return ok({ need_resend: gap, stored_count: settledIds.size });
  }
  if (row.completed_at === null) {
    await env.DB.prepare("UPDATE part2_session SET completed_at = ? WHERE id = ? AND completed_at IS NULL").bind(nowIso(), part2Id).run();
  }
  const correct = (held.results ?? []).filter((r) => r.final_answer !== null && isRight(r.final_answer, GOLD[r.item_id])).length;
  return ok({ correct_total: correct, total: ITEMS.length });
}

export async function resume(env: Part2Env, part2Id: string): Promise<Reply> {
  const row = await part2For(env, part2Id);
  if (row === null || row.declined) return no(404, UNKNOWN);
  return ok(await state(env, row));
}

/** Counts only, like part 1's: started and finished by arm, declines, never an answer. */
export async function counts(env: Part2Env): Promise<Reply> {
  const byArm: Record<string, { randomized: number; completed: number }> = {};
  for (const arm of PART2_ARMS) {
    const r = await env.DB.prepare(
      "SELECT COUNT(*) AS n, SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) AS done FROM part2_session WHERE arm = ? AND declined = 0 AND is_test = 0",
    )
      .bind(arm)
      .first<{ n: number; done: number | null }>();
    byArm[arm] = { randomized: Number(r?.n ?? 0), completed: Number(r?.done ?? 0) };
  }
  const d = await env.DB.prepare("SELECT COUNT(*) AS n FROM part2_session WHERE declined = 1 AND is_test = 0").first<{ n: number }>();
  return ok({ by_arm: byArm, declined: Number(d?.n ?? 0) });
}

/** Judge mode: always the assisted arm, feedback on each answer, nothing stored. */
export function demo(body: Record<string, unknown>): Reply {
  const itemId = String(body.item_id ?? "");
  const given = String(body.answer ?? "");
  if (!(itemId in GOLD)) return no(404, "We do not know that photo.");
  if (!ANSWERS.includes(given)) return no(422, "We do not know that answer.");
  return ok({ ask: questionNeeded("assisted", FLAGS[itemId] ?? null, given), correct: isRight(given, GOLD[itemId]) });
}

/** The two CSV files the export adds, with the columns evals/assist_analysis.py reads. */
export async function exportFiles(env: Part2Env, csvRow: (cells: unknown[]) => string): Promise<{ name: string; text: string }[]> {
  const sessions = await env.DB.prepare("SELECT * FROM part2_session ORDER BY offered_at").all<Record<string, unknown>>();
  const responses = await env.DB.prepare("SELECT * FROM part2_response ORDER BY part2_id, position").all<Record<string, unknown>>();
  const firstAt: Record<string, string> = {};
  for (const r of responses.results ?? []) {
    const id = String(r.part2_id);
    const at = String(r.received_at);
    if (!firstAt[id] || at < firstAt[id]) firstAt[id] = at;
  }
  const sLines = [csvRow(PART2_SESSION_COLUMNS)];
  for (const s of sessions.results ?? []) {
    const first = firstAt[String(s.id)];
    const seconds = s.completed_at && first ? Math.round(((Date.parse(String(s.completed_at)) - Date.parse(first)) / 1000) * 10) / 10 : "";
    sLines.push(
      csvRow([
        s.id, s.session_id, s.part1_arm, s.arm ?? "", s.block_id ?? "", s.offered_at, s.declined, s.started_at ?? "",
        s.completed_at ?? "", seconds, s.client_token_hash, s.is_test, s.post_lock,
      ]),
    );
  }
  const feature = Object.fromEntries(ITEMS.map((i) => [i.id, i.feature]));
  const rLines = [csvRow(PART2_RESPONSE_COLUMNS)];
  for (const r of responses.results ?? []) {
    const id = String(r.item_id);
    const final = r.final_answer === null ? "" : String(r.final_answer);
    rLines.push(
      csvRow([
        r.part2_id, id, feature[id] ?? "", GOLD[id] ?? "", r.position, r.first_answer, final, r.question_shown,
        r.choice ?? "", r.t_first_ms ?? "", r.t_final_ms ?? "", final && GOLD[id] && isRight(final, GOLD[id]) ? 1 : 0,
      ]),
    );
  }
  return [
    { name: "part2_sessions.csv", text: sLines.join("\r\n") + "\r\n" },
    { name: "part2_responses.csv", text: rLines.join("\r\n") + "\r\n" },
  ];
}

export const PART2_SESSION_COLUMNS = [
  "part2_id", "session_id", "part1_arm", "arm", "block_id", "offered_at_utc", "declined", "started_at_utc",
  "completed_at_utc", "test_seconds", "client_token_hash", "is_test", "post_lock",
];
export const PART2_RESPONSE_COLUMNS = [
  "part2_id", "item_id", "feature", "gold", "position", "first_answer", "final_answer", "question_shown", "choice",
  "t_first_ms", "t_final_ms", "correct",
];
