// The study API on Cloudflare Workers and D1 (Update 09 section 2).
//
// Why TypeScript and not the tested Python: Python Workers do run FastAPI, but D1 is a prepared
// statement binding, not a DBAPI connection, so SQLModel and SQLAlchemy cannot reach it without
// a DBAPI shim nobody has written. docs/notes/hosting.md records the probe.
//
// Randomization is NOT reimplemented here. core/allocator.py stays the single source of truth:
// scripts/seed_arms.py writes its sequence into the arm_slot table and this Worker only takes the
// next slot, so core.allocator.replay still checks every stored assignment.

import CONTENT from "./content.json";

export interface Env {
  DB: D1Database;
  PHOTOS: KVNamespace;
  QA_KEY?: string;
  EXPORT_TOKEN?: string;
  ALLOWED_ORIGIN?: string;
}

const DATA_LOCK_UTC = Date.parse("2026-09-28T01:00:00Z");
const SOURCE_LABELS = ["poster", "chat", "friends", "creek_group", "other"];
const UA_CLASSES = ["phone", "tablet", "desktop", "other"];
const ANSWERS = ["yes", "no", "cant_tell"];
const TOKEN_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"; // no 0, o, 1, l or i, so it can be read aloud
const TOKEN_LENGTH = 16;

type Gold = "present" | "absent";
const GOLD: Record<string, Gold> = Object.fromEntries(CONTENT.test_items.map((i) => [i.id, i.gold as Gold]));
const FEATURE: Record<string, string> = Object.fromEntries(CONTENT.test_items.map((i) => [i.id, i.feature]));
const ITEM_IDS: string[] = CONTENT.test_items.map((i) => i.id);

function isCorrect(answer: string, gold: Gold): boolean {
  return (answer === "yes" && gold === "present") || (answer === "no" && gold === "absent");
}

async function sha256Hex(text: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, "0")).join("");
}

function randomHex(bytes: number): string {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}

function newContributorToken(): string {
  const a = new Uint32Array(TOKEN_LENGTH);
  crypto.getRandomValues(a);
  return Array.from(a, (n) => TOKEN_ALPHABET[n % TOKEN_ALPHABET.length]).join("");
}

/** Fisher Yates on a crypto source. The item order is per sitting and is stored, so it never
 *  has to match what Python would have produced. */
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

/** Constant time compare, so a wrong token cannot be found one character at a time. */
function sameSecret(given: string | null, expected: string | undefined): boolean {
  if (!expected || expected.length < 16 || !given || given.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= given.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}

const coerce = (raw: unknown, allowed: string[], fallback: string) =>
  typeof raw === "string" && allowed.includes(raw) ? raw : fallback;

function corsHeaders(env: Env): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN ?? "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type, x-qa-key",
    "Access-Control-Max-Age": "86400",
  };
}

const json = (env: Env, data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...corsHeaders(env) },
  });

const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, "Z");

// ---------------------------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------------------------

async function createSession(env: Env, body: Record<string, unknown>, isTest: boolean) {
  const raw = String(body.client_token_hash ?? "");
  if (raw.length < 8) return json(env, { detail: "client_token_hash is required." }, 422);
  const tokenHash = (await sha256Hex(raw)).slice(0, 32);

  // One browser keeps one arm, so reloading cannot let anyone shop for the other one.
  const earlier = await env.DB.prepare(
    "SELECT arm, block_id FROM session WHERE client_token_hash = ? ORDER BY started_at LIMIT 1",
  )
    .bind(tokenHash)
    .first<{ arm: string; block_id: number }>();

  // Take the next slot and read its pre-registered arm in one go.
  const taken = await env.DB.prepare(
    "UPDATE counter SET next_position = next_position + 1 WHERE id = 1 RETURNING next_position",
  ).first<{ next_position: number }>();
  if (taken === null) return json(env, { detail: "The randomization counter is missing." }, 500);
  const position = Number(taken.next_position) - 1;
  const slot = await env.DB.prepare("SELECT arm, block_id FROM arm_slot WHERE position = ?")
    .bind(position)
    .first<{ arm: string; block_id: number }>();
  if (slot === null) return json(env, { detail: "The randomization sequence has run out." }, 500);

  const arm = earlier && !isTest ? earlier.arm : slot.arm;
  const blockId = earlier && !isTest ? earlier.block_id : slot.block_id;
  const sessionId = randomHex(16);
  const order = shuffled(ITEM_IDS);
  const at = nowIso();
  const hidden = String(body.hidden_field ?? "").trim().length > 0;
  const warmup = typeof body.warmup_choice === "string" && CONTENT.warmup_ids.includes(body.warmup_choice) ? body.warmup_choice : null;

  await env.DB.prepare(
    `INSERT INTO session (id, arm, block_id, item_order, consent_version, content_hash, build_hash,
       consent_at, started_at, client_token_hash, ua_class, is_test, source_label,
       hidden_field_filled, post_lock, warmup_choice)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(
      sessionId,
      arm,
      blockId,
      JSON.stringify(order),
      String(body.consent_version ?? "").slice(0, 32),
      String(body.content_hash ?? "").slice(0, 64),
      String(body.build_hash ?? "").slice(0, 64),
      at,
      at,
      tokenHash,
      coerce(body.ua_class, UA_CLASSES, "other"),
      isTest ? 1 : 0,
      coerce(body.source_label, SOURCE_LABELS, "other"),
      hidden ? 1 : 0,
      Date.now() >= DATA_LOCK_UTC ? 1 : 0,
      warmup,
    )
    .run();

  return json(env, { session_id: sessionId, arm, item_order: order, lesson_first: arm === "trained" });
}

async function recordResponse(env: Env, body: Record<string, unknown>) {
  const sessionId = String(body.session_id ?? "");
  const itemId = String(body.item_id ?? "");
  const answer = String(body.answer ?? "");
  if (!ANSWERS.includes(answer)) return json(env, { detail: "We do not know that answer." }, 422);
  const session = await env.DB.prepare("SELECT id FROM session WHERE id = ?").bind(sessionId).first();
  if (session === null) return json(env, { detail: "We do not know that session. Start again from the first screen." }, 404);
  if (!(itemId in GOLD)) return json(env, { detail: "We do not know that test item." }, 404);

  const existing = await env.DB.prepare("SELECT answer FROM response WHERE session_id = ? AND item_id = ?")
    .bind(sessionId, itemId)
    .first<{ answer: string }>();
  if (existing !== null) {
    // Idempotent: the same answer again is fine, a different one keeps the first.
    if (existing.answer !== answer) return json(env, { detail: "This photo already has an answer. The first answer stays." }, 409);
    return json(env, { ok: true });
  }
  await env.DB.prepare(
    `INSERT OR IGNORE INTO response (session_id, item_id, answer, rt_ms, position,
       first_choice, t_first_ms, n_changes, received_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(
      sessionId,
      itemId,
      answer,
      Number(body.rt_ms ?? 0),
      Number(body.position ?? 0),
      typeof body.first_choice === "string" ? body.first_choice : null,
      body.t_first_ms === undefined || body.t_first_ms === null ? null : Number(body.t_first_ms),
      Number(body.n_changes ?? 0),
      nowIso(),
    )
    .run();
  return json(env, { ok: true });
}

async function scoresFor(env: Env, sessionId: string) {
  const rows = await env.DB.prepare("SELECT item_id, answer FROM response WHERE session_id = ?")
    .bind(sessionId)
    .all<{ item_id: string; answer: string }>();
  const byFeature: Record<string, { feature: string; correct: number; total: number }> = {};
  for (const f of CONTENT.features) byFeature[f] = { feature: f, correct: 0, total: 0 };
  for (const item of CONTENT.test_items) byFeature[item.feature].total += 1;
  for (const r of rows.results ?? []) {
    const gold = GOLD[r.item_id];
    if (gold && isCorrect(r.answer, gold)) byFeature[FEATURE[r.item_id]].correct += 1;
  }
  const scores = CONTENT.features.map((f) => byFeature[f]);
  return { scores, correct_total: scores.reduce((n, s) => n + s.correct, 0), held: (rows.results ?? []).length };
}

async function completeSession(env: Env, body: Record<string, unknown>) {
  const sessionId = String(body.session_id ?? "");
  const row = await env.DB.prepare("SELECT item_order, completed_at FROM session WHERE id = ?")
    .bind(sessionId)
    .first<{ item_order: string; completed_at: string | null }>();
  if (row === null) return json(env, { detail: "We do not know that session. Start again from the first screen." }, 404);

  const order: string[] = JSON.parse(row.item_order);
  const held = await env.DB.prepare("SELECT item_id FROM response WHERE session_id = ?")
    .bind(sessionId)
    .all<{ item_id: string }>();
  const have = new Set((held.results ?? []).map((r) => r.item_id));
  const gap = order.filter((id) => !have.has(id));
  const answeredCount = Number(body.answered_count ?? 0);
  const isFinal = body.final === true;

  // The end screen waits until we hold every answer. See docs/CONTRACTS.md.
  if (gap.length > 0 && !isFinal && row.completed_at === null && answeredCount > have.size) {
    return json(env, { need_resend: gap, stored_count: have.size });
  }

  const { scores, correct_total } = await scoresFor(env, sessionId);
  const out: Record<string, unknown> = { scores, correct_total };
  if (row.completed_at === null) {
    const prior = body.prior_experience === "yes" || body.prior_experience === "no" ? body.prior_experience : null;
    await env.DB.prepare("UPDATE session SET completed_at = ?, prior_experience = ?, unsent_count = ? WHERE id = ?")
      .bind(nowIso(), prior, Math.max(0, answeredCount - have.size), sessionId)
      .run();
  }
  if (body.keep_score === true) {
    const token = newContributorToken();
    await env.DB.prepare("INSERT INTO observer (contributor_token, scores_json, tested_on) VALUES (?, ?, ?)")
      .bind(token, JSON.stringify(scores), nowIso().slice(0, 10))
      .run();
    out.contributor_token = token;
  }
  return json(env, out);
}

async function resumeState(env: Env, sessionId: string) {
  const row = await env.DB.prepare(
    "SELECT id, arm, item_order, lesson_seconds, completed_at FROM session WHERE id = ?",
  )
    .bind(sessionId)
    .first<{ id: string; arm: string; item_order: string; lesson_seconds: string | null; completed_at: string | null }>();
  if (row === null) return json(env, { detail: "We do not know that session. Start again from the first screen." }, 404);
  const answered = await env.DB.prepare("SELECT item_id FROM response WHERE session_id = ? ORDER BY position")
    .bind(sessionId)
    .all<{ item_id: string }>();
  const state: Record<string, unknown> = {
    session_id: row.id,
    arm: row.arm,
    item_order: JSON.parse(row.item_order),
    lesson_first: row.arm === "trained",
    lesson_done: Boolean(row.lesson_seconds),
    answered: (answered.results ?? []).map((r) => r.item_id),
    completed: row.completed_at !== null,
  };
  if (row.completed_at !== null) {
    const { scores, correct_total } = await scoresFor(env, sessionId);
    state.scores = scores;
    state.correct_total = correct_total;
  }
  return json(env, state);
}

async function counts(env: Env) {
  const byArm: Record<string, { randomized: number; completed: number }> = {};
  for (const arm of ["untrained", "trained"]) {
    const r = await env.DB.prepare(
      "SELECT COUNT(*) AS n, SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) AS done FROM session WHERE arm = ? AND is_test = 0",
    )
      .bind(arm)
      .first<{ n: number; done: number | null }>();
    byArm[arm] = { randomized: Number(r?.n ?? 0), completed: Number(r?.done ?? 0) };
  }
  const bySource: Record<string, number> = Object.fromEntries(SOURCE_LABELS.map((s) => [s, 0]));
  const rows = await env.DB.prepare(
    "SELECT source_label, COUNT(*) AS n FROM session WHERE is_test = 0 AND completed_at IS NOT NULL GROUP BY source_label",
  ).all<{ source_label: string; n: number }>();
  for (const r of rows.results ?? []) bySource[coerce(r.source_label, SOURCE_LABELS, "other")] += Number(r.n);
  const post = await env.DB.prepare("SELECT COUNT(*) AS n FROM session WHERE is_test = 0 AND post_lock = 1").first<{ n: number }>();
  return json(env, { by_arm: byArm, by_source: bySource, post_lock: Number(post?.n ?? 0) });
}

// A store only zip, so the export keeps the two file shape docs/CONTRACTS.md promises without
// pulling a compression library into the Worker.
function crc32(bytes: Uint8Array): number {
  let c = 0xffffffff;
  for (const b of bytes) {
    c ^= b;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  return (c ^ 0xffffffff) >>> 0;
}

function zipOf(files: { name: string; text: string }[]): Uint8Array {
  const enc = new TextEncoder();
  const chunks: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let offset = 0;
  for (const f of files) {
    const name = enc.encode(f.name);
    const data = enc.encode(f.text);
    const crc = crc32(data);
    const local = new Uint8Array(30 + name.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 0x04034b50, true);
    lv.setUint16(4, 20, true);
    lv.setUint16(8, 0, true);
    lv.setUint32(14, crc, true);
    lv.setUint32(18, data.length, true);
    lv.setUint32(22, data.length, true);
    lv.setUint16(26, name.length, true);
    local.set(name, 30);
    chunks.push(local, data);
    const head = new Uint8Array(46 + name.length);
    const hv = new DataView(head.buffer);
    hv.setUint32(0, 0x02014b50, true);
    hv.setUint16(4, 20, true);
    hv.setUint16(6, 20, true);
    hv.setUint32(16, crc, true);
    hv.setUint32(20, data.length, true);
    hv.setUint32(24, data.length, true);
    hv.setUint16(28, name.length, true);
    hv.setUint32(42, offset, true);
    head.set(name, 46);
    central.push(head);
    offset += local.length + data.length;
  }
  const centralSize = central.reduce((n, c) => n + c.length, 0);
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, files.length, true);
  ev.setUint16(10, files.length, true);
  ev.setUint32(12, centralSize, true);
  ev.setUint32(16, offset, true);
  const total = offset + centralSize + 22;
  const out = new Uint8Array(total);
  let at = 0;
  for (const c of [...chunks, ...central, end]) {
    out.set(c, at);
    at += c.length;
  }
  return out;
}

const csvCell = (v: unknown) => {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
const csvRow = (cells: unknown[]) => cells.map(csvCell).join(",");

async function exportZip(env: Env) {
  const sessions = await env.DB.prepare("SELECT * FROM session ORDER BY started_at").all<Record<string, unknown>>();
  const responses = await env.DB.prepare("SELECT * FROM response ORDER BY session_id, position").all<Record<string, unknown>>();
  const firstAt: Record<string, string> = {};
  for (const r of responses.results ?? []) {
    const sid = String(r.session_id);
    const at = String(r.received_at);
    if (!firstAt[sid] || at < firstAt[sid]) firstAt[sid] = at;
  }
  const sessionHead = [
    "session_id", "arm", "block_id", "source_label", "ua_class", "consent_version", "content_hash",
    "build_hash", "started_at_utc", "lesson_seconds_total", "completed_at_utc", "test_seconds",
    "is_test", "post_lock", "hidden_field_filled", "client_token_hash", "prior_experience",
    "warmup_choice", "unsent_count",
  ];
  const sessionLines = [csvRow(sessionHead)];
  for (const s of sessions.results ?? []) {
    let lessonTotal: string | number = "";
    if (s.lesson_seconds) {
      const vals: number[] = Object.values(JSON.parse(String(s.lesson_seconds)));
      lessonTotal = Math.round(vals.reduce((a, b) => a + b, 0) * 10) / 10;
    }
    let testSeconds: string | number = "";
    const first = firstAt[String(s.id)];
    if (s.completed_at && first) {
      testSeconds = Math.round(((Date.parse(String(s.completed_at)) - Date.parse(first)) / 1000) * 10) / 10;
    }
    sessionLines.push(
      csvRow([
        s.id, s.arm, s.block_id, s.source_label, s.ua_class, s.consent_version, s.content_hash,
        s.build_hash, s.started_at, lessonTotal, s.completed_at ?? "", testSeconds, s.is_test,
        s.post_lock, s.hidden_field_filled, s.client_token_hash, s.prior_experience ?? "",
        s.warmup_choice ?? "", s.unsent_count,
      ]),
    );
  }
  const responseHead = [
    "session_id", "item_id", "feature", "gold", "answer", "correct", "rt_ms", "position",
    "first_choice", "final_choice", "t_first_ms", "t_confirm_ms", "n_changes",
  ];
  const responseLines = [csvRow(responseHead)];
  for (const r of responses.results ?? []) {
    const itemId = String(r.item_id);
    const gold = GOLD[itemId];
    responseLines.push(
      csvRow([
        r.session_id, itemId, FEATURE[itemId] ?? "", gold ?? "", r.answer,
        gold && isCorrect(String(r.answer), gold) ? 1 : 0, r.rt_ms, r.position,
        r.first_choice ?? "", r.answer, r.t_first_ms ?? "", r.rt_ms, r.n_changes,
      ]),
    );
  }
  const zip = zipOf([
    { name: "sessions.csv", text: sessionLines.join("\r\n") + "\r\n" },
    { name: "responses.csv", text: responseLines.join("\r\n") + "\r\n" },
  ]);
  return new Response(zip, {
    status: 200,
    headers: {
      "content-type": "application/zip",
      "content-disposition": 'attachment; filename="second-look-export.zip"',
      "cache-control": "no-store",
      ...corsHeaders(env),
    },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(env) });

    if (path === "/health") return json(env, { status: "ok" });

    // P1's walking skeleton: one row written to the production database and read back.
    if (path === "/api/skeleton") {
      const note = `p1 ${nowIso()}`;
      await env.DB.prepare("INSERT INTO skeleton_ping (note, created_at) VALUES (?, ?)").bind(note, nowIso()).run();
      const back = await env.DB.prepare("SELECT id, note, created_at FROM skeleton_ping ORDER BY id DESC LIMIT 1").first();
      const total = await env.DB.prepare("SELECT COUNT(*) AS n FROM skeleton_ping").first<{ n: number }>();
      return json(env, { wrote: note, read_back: back, rows: Number(total?.n ?? 0) });
    }

    if (path === "/api/content/hash") return json(env, { content_hash: CONTENT.content_hash, build_hash: "worker" });

    let body: Record<string, unknown> = {};
    if (request.method === "POST" && (request.headers.get("content-type") ?? "").includes("application/json")) {
      try {
        body = (await request.json()) as Record<string, unknown>;
      } catch {
        return json(env, { detail: "That was not JSON." }, 400);
      }
    }

    try {
      if (path === "/api/test/session" && request.method === "POST") {
        const isTest = sameSecret(request.headers.get("x-qa-key"), env.QA_KEY);
        return await createSession(env, body, isTest);
      }
      if (path === "/api/test/response" && request.method === "POST") return await recordResponse(env, body);
      if (path === "/api/test/lesson-done" && request.method === "POST") {
        const sid = String(body.session_id ?? "");
        const seconds = (body.lesson_seconds ?? {}) as Record<string, number>;
        const clean: Record<string, number> = {};
        for (const [k, v] of Object.entries(seconds)) clean[k.slice(0, 32)] = Math.round(Number(v) * 10) / 10;
        const r = await env.DB.prepare("UPDATE session SET lesson_seconds = ? WHERE id = ?").bind(JSON.stringify(clean), sid).run();
        if (!r.meta.changes) return json(env, { detail: "We do not know that session. Start again from the first screen." }, 404);
        return json(env, { ok: true });
      }
      if (path === "/api/test/complete" && request.method === "POST") return await completeSession(env, body);
      if (path === "/api/test/resume") return await resumeState(env, url.searchParams.get("session_id") ?? "");
      if (path === "/api/test/counts") return await counts(env);
      if (path === "/api/test/export") {
        if (!sameSecret(url.searchParams.get("token"), env.EXPORT_TOKEN)) return json(env, { detail: "Not found." }, 404);
        return await exportZip(env);
      }
      if (path === "/api/demo/answer" && request.method === "POST") {
        const gold = GOLD[String(body.item_id ?? "")];
        if (!gold) return json(env, { detail: "We do not know that test item." }, 404);
        // Only whether they were right. The gold label itself never leaves the server.
        return json(env, { correct: isCorrect(String(body.answer ?? ""), gold) });
      }
    } catch (err) {
      return json(env, { detail: "The server could not take that. Try again in a moment.", error: String(err) }, 500);
    }
    return json(env, { detail: "Not found." }, 404);
  },
};
