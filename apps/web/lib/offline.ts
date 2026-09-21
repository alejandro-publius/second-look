// The offline queue for creek checks. Drafts and downsized photos wait in IndexedDB on the phone
// and are sent on the next visit, when the network returns, or by the service worker's sync event.
import { api, isNetworkError, type DraftRequest } from "./api";

const DB_NAME = "second-look";
const STORE = "queue";
const EVENT = "sl-queue";

export interface QueuedPhoto {
  name: string;
  type: string;
  blob: Blob;
}

export interface QueuedCheck {
  id?: number;
  kind: "check" | "quick";
  created_at: string;
  spot_id?: string;
  draft?: DraftRequest;
  quick?: { spot_id: string; body: Record<string, unknown> };
  photos: QueuedPhoto[];
  status: "waiting" | "sending" | "sent" | "failed";
  result?: { visit_id?: string; spot_id?: string };
  error?: string;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("no indexeddb"));
      return;
    }
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error("indexeddb open failed"));
  });
}

function tx<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const t = db.transaction(STORE, mode);
        const req = run(t.objectStore(STORE));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error ?? new Error("indexeddb request failed"));
        t.oncomplete = () => db.close();
      }),
  );
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
    item.error = err instanceof Error ? err.message : String(err);
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
