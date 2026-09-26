// The walk clips, served in parts (critic round 15 W05, UPDATE_32 section 4). Pages answers a
// request for part of a static file (a range request) with 200 and the whole file, and then
// Chrome cannot seek: every move of the slider starts the clip again. public/_routes.json sends
// /walks/* here; this Function reads the same static file through env.ASSETS and answers a
// Range header with 206 Partial Content and only the bytes asked for. No storage product is
// involved: the clips are still the files in out/walks/ that every web deploy uploads.
//
// One file with no imports, like the other Functions, so tests/walk-range.spec.ts can load it as
// it is. Only the bytes unit and a single range are served; anything else gets the whole file,
// which a server may always do (RFC 9110 section 14.2).

const CACHE = "public, max-age=3600";

/**
 * What a Range header asks of a file of `size` bytes: null for the whole file (no header, a unit
 * other than bytes, several ranges, or a header that does not parse), "unsatisfiable" for a range
 * that starts past the end, or the first and last byte, both included.
 */
export function parseRange(header, size) {
  if (!header) return null;
  const m = /^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*$/i.exec(header);
  if (!m) return null;
  const [, first, last] = m;
  if (first === "" && last === "") return null;
  if (first === "") {
    const suffix = Number(last);
    if (suffix === 0 || size === 0) return "unsatisfiable";
    return { start: Math.max(0, size - suffix), end: size - 1 };
  }
  const start = Number(first);
  if (last !== "" && Number(last) < start) return null;
  if (start >= size) return "unsatisfiable";
  const end = last === "" ? size - 1 : Math.min(Number(last), size - 1);
  return { start, end };
}

/**
 * Bytes start to end, both included, out of a stream of the whole file. On Cloudflare the result
 * goes through a FixedLengthStream, because the runtime drops a Content-Length header set by hand
 * on a streamed body and would send the part chunked, with no length.
 */
function slice(body, start, end) {
  let seen = 0;
  const part = body.pipeThrough(
    new TransformStream({
      transform(chunk, controller) {
        const at = seen;
        seen += chunk.byteLength;
        const from = Math.max(start - at, 0);
        const to = Math.min(end + 1 - at, chunk.byteLength);
        if (from < to) controller.enqueue(chunk.subarray(from, to));
        if (seen > end) controller.terminate();
      },
    }),
  );
  return typeof FixedLengthStream === "function" ? part.pipeThrough(new FixedLengthStream(end - start + 1)) : part;
}

/**
 * The answer to `request` given the whole file as `asset` (a 200 from the static store): 206 with
 * the part asked for, 416 for a range past the end, or 200 with the whole file. A HEAD gets the
 * same status and headers with no body.
 */
export async function rangeResponse(request, asset) {
  const headers = new Headers(asset.headers);
  headers.set("Accept-Ranges", "bytes");
  headers.set("Cache-Control", CACHE);
  headers.delete("Content-Range");
  if (!headers.get("Content-Type")) headers.set("Content-Type", "video/mp4");
  let body = asset.body;
  let size = Number(asset.headers.get("Content-Length"));
  if (!asset.headers.has("Content-Length") || !Number.isSafeInteger(size)) {
    const bytes = new Uint8Array(await asset.arrayBuffer());
    size = bytes.byteLength;
    body = new Blob([bytes]).stream();
  }
  const head = request.method === "HEAD";
  const whole = () => {
    headers.set("Content-Length", String(size));
    if (head) body?.cancel();
    return new Response(head ? null : body, { status: 200, headers });
  };

  // If-Range: the part is only good for the same version of the file, known by a strong tag. When
  // the tag differs, is weak, or is a date, the whole file is sent instead.
  const ifRange = request.headers.get("If-Range");
  const etag = headers.get("ETag") ?? "";
  if (ifRange && (ifRange !== etag || etag.startsWith("W/"))) return whole();
  const range = parseRange(request.headers.get("Range"), size);
  if (range === null) return whole();
  if (range === "unsatisfiable") {
    body?.cancel();
    headers.set("Content-Range", `bytes */${size}`);
    headers.set("Content-Length", "0");
    return new Response(null, { status: 416, headers });
  }
  const { start, end } = range;
  headers.set("Content-Range", `bytes ${start}-${end}/${size}`);
  headers.set("Content-Length", String(end - start + 1));
  if (head) body?.cancel();
  return new Response(head ? null : slice(body, start, end), { status: 206, headers });
}

/** Pages calls this for every /walks/* request (public/_routes.json). */
export async function onRequest({ request, env }) {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response(null, { status: 405, headers: { Allow: "GET, HEAD" } });
  }
  // Ask the static store for the whole file, as it is, with no range and no compression, so the
  // byte counts here are the file's own.
  const forward = new Headers(request.headers);
  forward.delete("Range");
  forward.delete("If-Range");
  forward.set("Accept-Encoding", "identity");
  const asset = await env.ASSETS.fetch(new Request(request.url, { method: "GET", headers: forward }));
  if (asset.status !== 200) return asset;
  return rangeResponse(request, asset);
}
