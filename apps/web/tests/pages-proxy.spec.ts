import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { expect, test } from "@playwright/test";

// Playwright runs specs as CommonJS, so paths come from __dirname and the ES modules under test
// are loaded with a dynamic import of a file URL. The two Functions are .js files in a package
// without "type": "module", which Playwright's loader on Node 20 (CI) reads as CommonJS, so they
// are imported from their own source as a data URL, always an ES module. Neither imports anything.
const web = join(__dirname, "..");
const load = (relative: string) => import(pathToFileURL(join(web, relative)).href);
const loadFunction = (relative: string) =>
  import(`data:text/javascript;base64,${readFileSync(join(web, relative)).toString("base64")}`);

// Update 10 answer A1: the API sits behind /api/* on the Pages origin. Two small facts keep that
// honest without a network: the routes file sends /api/* and /health to the Function and keeps
// the static share cards out of it, and the Function hands the request to the bound Worker as is.

test("_routes.json sends the API to the Function and keeps the share cards static", async () => {
  const routes = JSON.parse(readFileSync(join(web, "public", "_routes.json"), "utf8"));
  expect(routes.version).toBe(1);
  expect(routes.include).toEqual(["/api/*", "/health"]);
  expect(routes.exclude).toEqual(["/api/share/*"]);
});

test("the Pages Function forwards the request unchanged to the API service binding", async () => {
  const seen: Request[] = [];
  const env = {
    API: {
      fetch: async (request: Request) => {
        seen.push(request);
        return new Response(JSON.stringify({ status: "ok" }), { headers: { "content-type": "application/json" } });
      },
    },
  };
  for (const file of ["functions/api/[[path]].js", "functions/health.js"]) {
    const mod = await loadFunction(file);
    const request = new Request("https://depth.second-look-79t.pages.dev/api/test/counts", {
      method: "POST",
      headers: { "content-type": "application/json", "x-qa-key": "abc" },
      body: JSON.stringify({ a: 1 }),
    });
    const response = await mod.onRequest({ request, env });
    expect(response.status).toBe(200);
    const forwarded = seen.at(-1)!;
    expect(forwarded.url).toBe(request.url);
    expect(forwarded.method).toBe("POST");
    expect(forwarded.headers.get("x-qa-key")).toBe("abc");
    expect(await forwarded.text()).toBe(JSON.stringify({ a: 1 }));
  }
});

test("with no API origin the policy allows 'self' only, and with one it names it", async () => {
  const { buildHeaders } = await load("security-headers.mjs");
  const same = buildHeaders({ apiOrigin: "" }).csp;
  expect(same).toContain("connect-src 'self';");
  expect(same).not.toContain("connect-src 'self' ;");
  const apart = buildHeaders({ apiOrigin: "https://api.example" }).csp;
  expect(apart).toContain("connect-src 'self' https://api.example;");
});
