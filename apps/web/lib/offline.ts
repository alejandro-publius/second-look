// The offline queue for creek checks and video walks. Drafts and downsized photos wait in
// IndexedDB on the phone and are sent on the next visit, when the network returns, or by the
// service worker's sync event. A finished walk waits here the same way until the store has kept
// its record (UPDATE_30 section 1 item 3).
//
// The same database holds each walk's answers while it is being made, keyed by the walk's id, so
// Back, a reload or a closed tab opens the walk where it was (UPDATE_30 section 1 item 2).
import { ApiError, api, isNetworkError, type AnswerValue, type DraftRequest, type WalkStoreRequest } from "./api";

const DB_NAME = "second-look";
// Version 2 added the walks store. The queue store and everything in it are kept.
const DB_VERSION = 2;
const STORE = "queue";
const WALKS = "walks";
const EVENT = "sl-queue";

export interface QueuedPhoto {
  name: string;
  type: string;
  blob: Blob;
}

export interface QueuedCheck {
  id?: number;
  kind: "check" | "quick" | "walk";
  created_at: string;
  spot_id?: string;
  draft?: DraftRequest;
  quick?: { spot_id: string; body: Record<string, unknown> };
  walk?: WalkStoreRequest;
  photos: QueuedPhoto[];
  status: "waiting" | "sending" | "sent" | "failed";
  result?: { visit_id?: string; spot_id?: string; record_id?: string; delete_after?: string };
  error?: string;
}

/**
 * One video walk on this device, by its walk id: the answers so far and the question to open on,
 * then, once finished, when it was finished and what the store did with it. At most one per walk:
 * Start again deletes it.
 */
export interface WalkState {
  walk_id: string;
  answers: Record<string, AnswerValue>;
  /** Where the walk opens: the index of the next unanswered question among those showing, or
   *  their count when every one is behind it and only the follow-ups or the checker's question are
   *  left. */
  next: number;
  /** Set when the walk is finished. The record is built from the answers and this time. */
  answered_at: string | null;
  /** The queue item that sends the finished walk to the store. */
  queue_id: number | null;
  record_id: string | null;
  delete_after: string | null;
  /** The answers to the follow-up questions the rules asked, and the rating the rating check left
   *  (judge walk W01). A walk kept before walks asked any has neither. */
  followup_answers?: Record<string, string>;
  final_rating?: string | null;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("no indexeddb"));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
      if (!db.objectStoreNames.contains(WALKS)) db.createObjectStore(WALKS, { keyPath: "walk_id" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error("indexeddb open failed"));
  });
}

/** One request in its own transaction. It resolves once the transaction has committed, not when
 *  the request succeeds, so a page closed or reloaded right after never loses what it was told
 *  had been kept (a walk's Start again, then a reload, reopened the walk it had set aside). */
function tx<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>, storeName: string = STORE): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const t = db.transaction(storeName, mode);
        const req = run(t.objectStore(storeName));
        let result: T;
        req.onsuccess = () => {
          result = req.result;
        };
        req.onerror = () => reject(req.error ?? new Error("indexeddb request failed"));
        t.oncomplete = () => {
          db.close();
          resolve(result);
        };
        t.onabort = () => {
          db.close();
          reject(t.error ?? new Error("indexeddb transaction aborted"));
        };
      }),
  );
}

/** The walk as this device holds it, or null. Null too where the browser has no IndexedDB. */
export function loadWalkState(walkId: string): Promise<WalkState | null> {
  return tx<WalkState | undefined>("readonly", (s) => s.get(walkId) as IDBRequest<WalkState | undefined>, WALKS)
    .then((w) => w ?? null)
    .catch(() => null);
}

/** Keeps the walk as it is now. A browser that refuses storage keeps nothing, and the walk goes on. */
export async function saveWalkState(state: WalkState): Promise<void> {
  try {
    await tx("readwrite", (s) => s.put(state), WALKS);
  } catch {
    // A private window can refuse IndexedDB. The walk on screen still works; it cannot resume.
  }
}

/** Start again: forgets this walk on this device. A stored record stays on the server. */
export async function deleteWalkState(walkId: string): Promise<void> {
  try {
    await tx("readwrite", (s) => s.delete(walkId), WALKS);
  } catch {
    // Nothing was kept, so there is nothing to forget.
  }
}

function announce(detail: unknown) {
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(EVENT, { detail }));
}

export function onQueueChange(handler: (detail: unknown) => void): () => void {
  const fn = (e: Event) => handler((e as CustomEvent).detail);
  window.addEventListener(EVENT, fn);
  return () => window.removeEventListener(EVENT, fn);
}

export async function enqueue(item: Omit<QueuedCheck, "id" | "status">): Promise<number> {
  const id = await tx<IDBValidKey>("readwrite", (s) => s.add({ ...item, status: "waiting" }));
  announce({ type: "added", id });
  return Number(id);
}

export function listQueue(): Promise<QueuedCheck[]> {
  return tx<QueuedCheck[]>("readonly", (s) => s.getAll() as IDBRequest<QueuedCheck[]>).catch(() => []);
}

export function getQueued(id: number): Promise<QueuedCheck | undefined> {
  return tx<QueuedCheck | undefined>("readonly", (s) => s.get(id) as IDBRequest<QueuedCheck | undefined>);
}

async function put(item: QueuedCheck): Promise<void> {
  await tx("readwrite", (s) => s.put(item));
  announce({ type: "updated", id: item.id, status: item.status });
}

export async function removeQueued(id: number): Promise<void> {
  await tx("readwrite", (s) => s.delete(id));
  announce({ type: "removed", id });
}

async function uploadAll(photos: QueuedPhoto[]): Promise<string[]> {
  const ids: string[] = [];
  for (const p of photos) {
    const { photo_id } = await api.upload(p.blob, p.name);
    ids.push(photo_id);
  }
  return ids;
}

/** Sends one queued item. Returns its status afterwards: sent, waiting (network) or failed (refused). */
export async function sendQueued(item: QueuedCheck): Promise<QueuedCheck["status"]> {
  if (item.status === "sent") return "sent";
  item.status = "sending";
  await put(item);
  try {
    if (item.kind === "check" && item.draft) {
      const photo_ids = await uploadAll(item.photos);
      const draft = await api.checkDraft({ ...item.draft, photo_ids: [...item.draft.photo_ids, ...photo_ids] });
      // The person has left the creek, so follow-ups cannot be asked now. Finalize with none and the
      // first rating as the final rating. Nothing is changed on their behalf.
      const fin = await api.checkFinalize({ draft_id: draft.draft_id, followup_answers: {}, final_rating: item.draft.first_rating });
      item.result = fin;
    } else if (item.kind === "quick" && item.quick) {
      const photo_ids = await uploadAll(item.photos);
      const body = { ...item.quick.body, ...(photo_ids[0] ? { photo_id: photo_ids[0] } : {}) };
      await api.quick(item.quick.spot_id, body as never);
      item.result = { spot_id: item.quick.spot_id };
    } else if (item.kind === "walk" && item.walk) {
      const stored = await api.storeWalk(item.walk);
      item.result = { record_id: stored.record_id, delete_after: stored.delete_after };
    }
    item.status = "sent";
    item.photos = [];
    await put(item);
    return "sent";
  } catch (err) {
    if (isNetworkError(err)) {
      item.status = "waiting";
      await put(item);
      return "waiting";
    }
    item.status = "failed";
    // The API's own sentence when it gave one, such as the walk store's daily cap.
    item.error = err instanceof ApiError && err.detail ? err.detail : err instanceof Error ? err.message : String(err);
    await put(item);
    return "failed";
  }
}

let flushing = false;

/** Tries to send everything that waits. Safe to call often. */
export async function flushQueue(): Promise<{ sent: number; waiting: number }> {
  if (flushing) return { sent: 0, waiting: 0 };
  flushing = true;
  let sent = 0;
  let waiting = 0;
  try {
    const items = await listQueue();
    for (const item of items) {
      if (item.status === "sent" || item.status === "failed") continue;
      const status = await sendQueued(item);
      if (status === "sent") sent += 1;
      else if (status === "waiting") waiting += 1;
    }
  } finally {
    flushing = false;
  }
  announce({ type: "flushed", sent, waiting });
  return { sent, waiting };
}

/** Wires the online event and a slow timer. Returns an unsubscribe function. */
export function startQueueWatcher(intervalMs = 5000): () => void {
  const onOnline = () => {
    void flushQueue();
  };
  window.addEventListener("online", onOnline);
  const timer = window.setInterval(() => {
    if (navigator.onLine) void flushQueue();
  }, intervalMs);
  void flushQueue();
  return () => {
    window.removeEventListener("online", onOnline);
    window.clearInterval(timer);
  };
}
