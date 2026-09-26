import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

// Critic round 15 W05 and UPDATE_32 section 4: Pages answers a range request for a walk clip with
// 200 and the whole file, so Chrome cannot seek in it. functions/walks/[[path]].js reads the clip
// from the static store and answers Range with 206 and only the bytes asked for. The Function is
// loaded from its own source as a data URL, as in pages-proxy.spec.ts, because it is a .js file in
// a package without "type": "module".
const web = join(__dirname, "..");
const loadFunction = () =>
  import(`data:text/javascript;base64,${readFileSync(join(web, "functions", "walks", "[[path]].js")).toString("base64")}`);

const SIZE = 1000;
const FILE = Uint8Array.from({ length: SIZE }, (_, i) => i % 251);
const ETAG = '"clip-v1"';
const URL_ = "https://second-look-79t.pages.dev/walks/v02.mp4";

/** The static store: the whole file with 200, whatever the request asked, as Pages does. */
function assets() {
  const seen: Request[] = [];
  return {
    seen,
    ASSETS: {
      fetch: async (request: Request) => {
        seen.push(request);
        if (!new URL(request.url).pathname.endsWith(".mp4")) return new Response("Not found", { status: 404 });
        return new Response(FILE.slice(), {
          status: 200,
          headers: { "content-type": "video/mp4", "content-length": String(SIZE), etag: ETAG },
        });
      },
    },
  };
}

async function ask(headers: Record<string, string> = {}, method = "GET") {
  const { onRequest } = await loadFunction();
  const env = assets();
  const response: Response = await onRequest({ request: new Request(URL_, { method, headers }), env });
  const body = new Uint8Array(await response.arrayBuffer());
  return { response, body, seen: env.seen };
}

test("a normal range gets 206 with exactly those bytes and the headers that say so", async () => {
  const { response, body, seen } = await ask({ Range: "bytes=0-99" });
  expect(response.status).toBe(206);
  expect(response.headers.get("content-range")).toBe(`bytes 0-99/${SIZE}`);
  expect(response.headers.get("content-length")).toBe("100");
  expect(response.headers.get("accept-ranges")).toBe("bytes");
  expect(response.headers.get("content-type")).toBe("video/mp4");
  expect(response.headers.get("etag")).toBe(ETAG);
  expect(response.headers.get("cache-control")).toBe("public, max-age=3600");
  expect(Array.from(body)).toEqual(Array.from(FILE.subarray(0, 100)));
  // The static store is asked for the whole file, with no range and no compression.
  expect(seen[0].headers.get("range")).toBeNull();
  expect(seen[0].headers.get("accept-encoding")).toBe("identity");
  expect(seen[0].method).toBe("GET");
});

test("a range in the middle, and one past the end, are cut to the file", async () => {
  const mid = await ask({ Range: "bytes=250-749" });
  expect(mid.response.status).toBe(206);
  expect(mid.response.headers.get("content-range")).toBe(`bytes 250-749/${SIZE}`);
  expect(Array.from(mid.body)).toEqual(Array.from(FILE.subarray(250, 750)));
  const over = await ask({ Range: "bytes=900-5000" });
  expect(over.response.status).toBe(206);
  expect(over.response.headers.get("content-range")).toBe(`bytes 900-999/${SIZE}`);
  expect(over.response.headers.get("content-length")).toBe("100");
  expect(over.body.byteLength).toBe(100);
});

test("an open-ended range bytes=100- runs to the last byte", async () => {
  const { response, body } = await ask({ Range: "bytes=100-" });
  expect(response.status).toBe(206);
  expect(response.headers.get("content-range")).toBe(`bytes 100-999/${SIZE}`);
  expect(response.headers.get("content-length")).toBe("900");
  expect(Array.from(body)).toEqual(Array.from(FILE.subarray(100)));
});

test("a suffix range bytes=-500 is the last 500 bytes, and a longer one is the whole file", async () => {
  const { response, body } = await ask({ Range: "bytes=-500" });
  expect(response.status).toBe(206);
  expect(response.headers.get("content-range")).toBe(`bytes 500-999/${SIZE}`);
  expect(response.headers.get("content-length")).toBe("500");
  expect(Array.from(body)).toEqual(Array.from(FILE.subarray(500)));
  const longer = await ask({ Range: "bytes=-5000" });
  expect(longer.response.status).toBe(206);
  expect(longer.response.headers.get("content-range")).toBe(`bytes 0-999/${SIZE}`);
  expect(longer.body.byteLength).toBe(SIZE);
});

test("a range that starts past the end gets 416 and the file's size", async () => {
  for (const range of [`bytes=${SIZE}-`, "bytes=5000-6000", "bytes=-0"]) {
    const { response, body } = await ask({ Range: range });
    expect(response.status, range).toBe(416);
    expect(response.headers.get("content-range"), range).toBe(`bytes */${SIZE}`);
    expect(response.headers.get("accept-ranges"), range).toBe("bytes");
    expect(body.byteLength, range).toBe(0);
  }
});

test("no Range gets 200 and the whole file, and says ranges are accepted", async () => {
  const { response, body } = await ask();
  expect(response.status).toBe(200);
  expect(response.headers.get("content-length")).toBe(String(SIZE));
  expect(response.headers.get("accept-ranges")).toBe("bytes");
  expect(response.headers.get("content-range")).toBeNull();
  expect(Array.from(body)).toEqual(Array.from(FILE));
});

test("a Range this Function does not serve gets the whole file, as a server may answer", async () => {
  for (const range of ["bytes=0-1,5-6", "items=0-5", "bytes=9-3", "bytes=-", "bytes=abc"]) {
    const { response, body } = await ask({ Range: range });
    expect(response.status, range).toBe(200);
    expect(body.byteLength, range).toBe(SIZE);
  }
});

test("If-Range with another version's tag gets the whole file; with this one, the part", async () => {
  const stale = await ask({ Range: "bytes=0-99", "If-Range": '"clip-v0"' });
  expect(stale.response.status).toBe(200);
  expect(stale.body.byteLength).toBe(SIZE);
  const same = await ask({ Range: "bytes=0-99", "If-Range": ETAG });
  expect(same.response.status).toBe(206);
  expect(same.body.byteLength).toBe(100);
});

test("HEAD gets the same status and headers as GET with no body", async () => {
  const part = await ask({ Range: "bytes=0-99" }, "HEAD");
  expect(part.response.status).toBe(206);
  expect(part.response.headers.get("content-range")).toBe(`bytes 0-99/${SIZE}`);
  expect(part.response.headers.get("content-length")).toBe("100");
  expect(part.body.byteLength).toBe(0);
  const whole = await ask({}, "HEAD");
  expect(whole.response.status).toBe(200);
  expect(whole.response.headers.get("content-length")).toBe(String(SIZE));
  expect(whole.response.headers.get("accept-ranges")).toBe("bytes");
  expect(whole.body.byteLength).toBe(0);
});

test("a file the store does not have stays its 404, and a POST is refused", async () => {
  const { onRequest } = await loadFunction();
  const missing: Response = await onRequest({ request: new Request("https://x.example/walks/none.txt"), env: assets() });
  expect(missing.status).toBe(404);
  const post: Response = await onRequest({ request: new Request(URL_, { method: "POST", body: "x" }), env: assets() });
  expect(post.status).toBe(405);
  expect(post.headers.get("allow")).toBe("GET, HEAD");
});

/** The whole file as a stream of 64 byte chunks, pulled one at a time, that notes when it is let go. */
function chunkedAsset() {
  const state = { pulled: 0, cancelled: false };
  let next = 0;
  const stream = new ReadableStream<Uint8Array>(
    {
      pull(controller) {
        if (next >= SIZE) return controller.close();
        state.pulled += 1;
        controller.enqueue(FILE.slice(next, next + 64));
        next += 64;
      },
      cancel() {
        state.cancelled = true;
      },
    },
    { highWaterMark: 0 },
  );
  const asset = new Response(stream, { headers: { "content-type": "video/mp4", "content-length": String(SIZE) } });
  return { asset, state };
}

test("a range that spans many chunks is cut at both ends, and the rest of the file is not read", async () => {
  const { rangeResponse } = await loadFunction();
  const { asset, state } = chunkedAsset();
  const response: Response = await rangeResponse(new Request(URL_, { headers: { Range: "bytes=100-299" } }), asset);
  expect(response.status).toBe(206);
  expect(Array.from(new Uint8Array(await response.arrayBuffer()))).toEqual(Array.from(FILE.subarray(100, 300)));
  // The pipe lets the source go a moment after the part closes.
  await new Promise((resolve) => setTimeout(resolve, 10));
  expect(state.cancelled).toBe(true);
  // Bytes 100 to 299 are in chunks 2 to 5; a chunk or two more may be in flight when it stops.
  expect(state.pulled).toBeLessThanOrEqual(7);
});

test("a HEAD and a 416 let the file's stream go without reading it", async () => {
  const { rangeResponse } = await loadFunction();
  for (const [method, range] of [["HEAD", "bytes=0-99"], ["HEAD", ""], ["GET", "bytes=5000-"]]) {
    const { asset, state } = chunkedAsset();
    const headers: Record<string, string> = range ? { Range: range } : {};
    await rangeResponse(new Request(URL_, { method, headers }), asset);
    expect(state.cancelled, `${method} ${range}`).toBe(true);
    expect(state.pulled, `${method} ${range}`).toBe(0);
  }
});

test("parseRange reads the five cases the walk player needs", async () => {
  const { parseRange } = await loadFunction();
  expect(parseRange("bytes=0-99", SIZE)).toEqual({ start: 0, end: 99 });
  expect(parseRange("bytes=100-", SIZE)).toEqual({ start: 100, end: 999 });
  expect(parseRange("bytes=-500", SIZE)).toEqual({ start: 500, end: 999 });
  expect(parseRange("bytes=1000-", SIZE)).toBe("unsatisfiable");
  expect(parseRange(null, SIZE)).toBeNull();
  expect(parseRange("bytes=0-", 0)).toBe("unsatisfiable");
});
