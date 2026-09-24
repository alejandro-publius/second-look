// The comparison render.mjs makes between a committed SVG and a fresh render. Run: node --test
import assert from "node:assert/strict";
import { test } from "node:test";
import { sha256, signature, splitStamp, stampFor, stampHead } from "./render.mjs";

const versions = { cli: "11.17.0", mermaid: "11.17.2" };
const svg = (x, label, cls = "node") =>
  `<svg viewBox="0 0 ${x} 100" style="max-width: ${x}px;"><g class="${cls}" transform="translate(${x / 2}, 12.5)">` +
  `<path d="M0,0L${x},3.25" data-points="W3sieCI6${x}fQ=="/><text y="-10.1">${label}</text></g></svg>\n`;

test("positions and sizes are set aside", () => {
  assert.equal(signature(svg(640, "a visit record")), signature(svg(652.75, "a visit record")));
});

test("a label that changed is not set aside", () => {
  assert.notEqual(signature(svg(640, "a visit record")), signature(svg(640, "a visit Record")));
});

test("a digit in a label is kept", () => {
  assert.notEqual(signature(svg(640, "guide at b907cf0")), signature(svg(640, "guide at b907cf1")));
});

test("a class or an element that changed is not set aside", () => {
  assert.notEqual(signature(svg(640, "x")), signature(svg(640, "x", "cluster")));
  assert.notEqual(signature(svg(640, "x")), signature(svg(640, "x").replace("<text", "<tspan").replace("</text>", "</tspan>")));
});

test("the stamp names the source, the config, the renderer and the drawing", () => {
  const body = svg(640, "x");
  const a = stampFor("ai-gate", "sequenceDiagram\n", "{}", versions, body);
  assert.match(a, /^<!-- Drawn by make diagrams from docs\/diagrams\/ai-gate\.mmd \(sha256 [0-9a-f]{64}\) /);
  assert.ok(a.startsWith(stampHead("ai-gate", "sequenceDiagram\n", "{}", versions)));
  assert.ok(!a.startsWith(stampHead("ai-gate", "sequenceDiagram\n  A->>B: x\n", "{}", versions)));
  assert.ok(!a.startsWith(stampHead("ai-gate", "sequenceDiagram\n", '{"theme":"dark"}', versions)));
  assert.ok(!a.startsWith(stampHead("ai-gate", "sequenceDiagram\n", "{}", { ...versions, mermaid: "11.18.0" })));
  assert.ok(!a.slice(4, -4).includes("--"), "an XML comment may not hold two hyphens in a row");
  assert.equal(signature(a + body), signature(body));
});

test("the drawing's sha256 in the stamp gives away a hand edit", () => {
  const body = svg(640, "x");
  const drawn = splitStamp(stampFor("ai-gate", "s", "{}", versions, body) + body);
  assert.equal(drawn.body, body);
  assert.equal(drawn.drawingSha, sha256(body));
  const moved = splitStamp(stampFor("ai-gate", "s", "{}", versions, body) + svg(652, "x"));
  assert.notEqual(moved.drawingSha, sha256(moved.body));
  assert.equal(splitStamp(body).drawingSha, null);
});
