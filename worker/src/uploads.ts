// Photo uploads on the Worker (hard rule 8): the real type is read from the first bytes, the size
// is capped, camera metadata is cut out of the file, the bytes live in KV for 30 days and are
// served back only with the one token the uploader was given. A port of the upload part of
// apps/api/check.py, without Pillow: the Worker cannot re-encode an image, so it removes the
// metadata segments instead, which is where EXIF, GPS and the camera's name live.

import { Invalid, NotFound, randomHex } from "./check";
import { sha256Hex } from "./core/sha256";

export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
export const KEEP_DAYS = 30;
const KEEP_SECONDS = KEEP_DAYS * 24 * 3600;

export class TooLarge extends Error {}

interface UploadEnv {
  DB: D1Database;
  PHOTOS: KVNamespace;
}

export function sniffImage(head: Uint8Array): "image/jpeg" | "image/png" | "image/webp" | null {
  if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) return "image/jpeg";
  if (head[0] === 0x89 && head[1] === 0x50 && head[2] === 0x4e && head[3] === 0x47 && head[4] === 0x0d && head[5] === 0x0a && head[6] === 0x1a && head[7] === 0x0a) return "image/png";
  if (String.fromCharCode(...head.slice(0, 4)) === "RIFF" && String.fromCharCode(...head.slice(8, 12)) === "WEBP") return "image/webp";
  return null;
}

/** JPEG: keep the picture, drop every APP1 to APP15 and COM segment (EXIF, XMP, ICC, comments).
 *  From the first scan onwards the bytes are copied as they are. */
export function stripJpeg(bytes: Uint8Array): Uint8Array {
  const out: Uint8Array[] = [bytes.slice(0, 2)];
  let i = 2;
  while (i + 4 <= bytes.length) {
    if (bytes[i] !== 0xff) break;
    const marker = bytes[i + 1];
    if (marker === 0xd8 || (marker >= 0xd0 && marker <= 0xd7) || marker === 0x01) {
      out.push(bytes.slice(i, i + 2));
      i += 2;
      continue;
    }
    if (marker === 0xda || marker === 0xd9) {
      out.push(bytes.slice(i));
      return concat(out);
    }
    const length = (bytes[i + 2] << 8) | bytes[i + 3];
    const end = i + 2 + length;
    const metadata = (marker >= 0xe1 && marker <= 0xef) || marker === 0xfe;
    if (!metadata) out.push(bytes.slice(i, end));
    i = end;
  }
  out.push(bytes.slice(i));
  return concat(out);
}

const PNG_DROP = new Set(["tEXt", "zTXt", "iTXt", "eXIf", "tIME"]);

/** PNG: drop the text, time and EXIF chunks, keep everything the picture needs. */
export function stripPng(bytes: Uint8Array): Uint8Array {
  const out: Uint8Array[] = [bytes.slice(0, 8)];
  let i = 8;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  while (i + 12 <= bytes.length) {
    const length = view.getUint32(i, false);
    const type = String.fromCharCode(...bytes.slice(i + 4, i + 8));
    const end = i + 12 + length;
    if (!PNG_DROP.has(type)) out.push(bytes.slice(i, Math.min(end, bytes.length)));
    i = end;
  }
  return concat(out);
}

/** WebP: drop the EXIF and XMP chunks and fix the RIFF size. */
export function stripWebp(bytes: Uint8Array): Uint8Array {
  const kept: Uint8Array[] = [];
  let i = 12;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  while (i + 8 <= bytes.length) {
    const fourcc = String.fromCharCode(...bytes.slice(i, i + 4));
    const size = view.getUint32(i + 4, true);
    const end = i + 8 + size + (size % 2);
    if (fourcc !== "EXIF" && fourcc !== "XMP ") kept.push(bytes.slice(i, Math.min(end, bytes.length)));
    i = end;
  }
  const body = concat(kept);
  const header = new Uint8Array(12);
  header.set(bytes.slice(0, 4));
  new DataView(header.buffer).setUint32(4, 4 + body.length, true);
  header.set(bytes.slice(8, 12), 8);
  return concat([header, body]);
}

function concat(parts: Uint8Array[]): Uint8Array {
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}

export function stripMetadata(bytes: Uint8Array, type: string): Uint8Array {
  if (type === "image/jpeg") return stripJpeg(bytes);
  if (type === "image/png") return stripPng(bytes);
  return stripWebp(bytes);
}

function urlSafeToken(bytes: number): string {
  const raw = crypto.getRandomValues(new Uint8Array(bytes));
  return btoa(String.fromCharCode(...raw)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export async function storeUpload(env: UploadEnv, request: Request, now: string): Promise<{ photo_id: string; token: string }> {
  const form = await request.formData().catch(() => null);
  const file = form?.get("file");
  if (!(file instanceof File)) throw new Invalid("Send the photo as a form field called file.");
  if (file.size > MAX_UPLOAD_BYTES) throw new TooLarge("That photo is over 8 MB. Send a smaller one.");
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (bytes.length > MAX_UPLOAD_BYTES) throw new TooLarge("That photo is over 8 MB. Send a smaller one.");
  const type = sniffImage(bytes.slice(0, 16));
  if (type === null) throw new Invalid("Only JPEG, PNG or WebP photos can be uploaded.");
  const clean = stripMetadata(bytes, type);
  const photoId = `up-${randomHex(8)}`;
  const token = urlSafeToken(24);
  // KV's own expiry is the 30 day deletion: nothing has to run to keep the promise.
  await env.PHOTOS.put(`photo:${photoId}`, clean, { expirationTtl: KEEP_SECONDS, metadata: { contentType: type } });
  await env.DB.prepare("INSERT INTO upload (photo_id, token_hash, content_type, size_bytes, created_at) VALUES (?, ?, ?, ?, ?)")
    .bind(photoId, sha256Hex(token), type, clean.length, now)
    .run();
  return { photo_id: photoId, token };
}

/** Constant time compare of two hex digests of equal length. */
function sameDigest(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function photoResponse(env: UploadEnv, photoId: string, token: string | null): Promise<Response> {
  const row = await env.DB.prepare("SELECT token_hash, content_type FROM upload WHERE photo_id = ?").bind(photoId).first<{ token_hash: string; content_type: string }>();
  if (row === null || !token || !sameDigest(sha256Hex(token), row.token_hash)) throw new NotFound("Not found.");
  const stored = await env.PHOTOS.get(`photo:${photoId}`, "arrayBuffer");
  if (stored === null) throw new NotFound("Not found.");
  return new Response(stored, {
    status: 200,
    headers: { "content-type": row.content_type, "cache-control": "private, no-store", "content-disposition": "inline", "x-content-type-options": "nosniff" },
  });
}
