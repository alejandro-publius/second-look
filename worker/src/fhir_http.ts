// How a FHIR resource leaves the Worker. FHIR R4 names application/fhir+json as the media type
// for JSON, and our Library entry lists the read only endpoint under it, so the routes that answer
// with a resource send that type, and an error on them is an OperationOutcome, the resource FHIR
// uses to say what went wrong. apps/api/fhir_http.py is the same in Python; the tests on both
// sides hold the same OperationOutcome, letter for letter.

import { escapeXml } from "./core/fhir_emit";

export const FHIR_JSON = "application/fhir+json; charset=utf-8";
export const PLAIN_JSON = "application/json; charset=utf-8";

// FHIR's own issue types (the IssueType value set), one per answer this API gives.
const ISSUE_CODES: Record<number, string> = {
  404: "not-found",
  409: "conflict",
  413: "too-long",
  422: "invalid",
  429: "throttled",
};

export interface OperationOutcome {
  resourceType: "OperationOutcome";
  text: { status: "generated"; div: string };
  issue: { severity: "error"; code: string; details: { text: string } }[];
}

/** The error as FHIR says it: one issue, with the same plain sentence the other routes give in
 *  detail. Any status without its own issue type is an exception, which is what a 500 is. */
export function operationOutcome(status: number, sentence: string): OperationOutcome {
  return {
    resourceType: "OperationOutcome",
    text: { status: "generated", div: `<div xmlns="http://www.w3.org/1999/xhtml"><p>${escapeXml(sentence)}</p></div>` },
    issue: [{ severity: "error", code: ISSUE_CODES[status] ?? "exception", details: { text: sentence } }],
  };
}

/** The media type for a FHIR answer. A browser that opens the link asks for text/html first, and
 *  some browsers save a type they do not know as a file, so it gets the same bytes as plain JSON
 *  and shows them in the tab. Everyone else (curl, a FHIR client, our own pages) gets FHIR's type. */
export function fhirMediaType(accept: string | null): string {
  return (accept ?? "").toLowerCase().includes("text/html") ? PLAIN_JSON : FHIR_JSON;
}
