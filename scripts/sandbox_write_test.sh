#!/usr/bin/env bash
# One-shot test of write access to the shared OneAquaHealth sandbox.
# Creates ONE small, tagged Location with a conditional create, reads it back,
# records its id in fhir/sandbox_ledger.jsonl, then deletes that id only.
# Never deletes by search. Never calls $expunge. Run from the repo root:
#   bash scripts/sandbox_write_test.sh | tee docs/notes/sandbox_write_test.txt
set -u
BASE="https://sandbox.hl7europe.eu/oneaquahealth/fhir"
REPO_URL="${REPO_URL:-https://github.com/alejandro-publius/second-look}"
TAG_SYSTEM="$REPO_URL"
TAG_CODE="write-test"
UA="second-look-sandbox-write-test (+$REPO_URL)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
IDENT="second-look-write-test-$STAMP"
LEDGER="fhir/sandbox_ledger.jsonl"
mkdir -p fhir
BODY=$(cat <<JSON
{"resourceType":"Location","meta":{"tag":[{"system":"$TAG_SYSTEM","code":"$TAG_CODE"}]},
 "identifier":[{"system":"$REPO_URL/write-test","value":"$IDENT"}],
 "name":"Second Look sandbox write test. Safe to delete.","mode":"instance"}
JSON
)
echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "base: $BASE"
echo "--- 1. conditional create"
CREATE=$(curl -sS -m 30 -o /tmp/swt_create.json -w '%{http_code}' -X POST "$BASE/Location" \
  -H "Content-Type: application/fhir+json" -H "Accept: application/fhir+json" \
  -H "If-None-Exist: identifier=$REPO_URL/write-test|$IDENT" -H "User-Agent: $UA" \
  --data "$BODY")
echo "create_status: $CREATE"
ID=$(python3 -c 'import json,sys; print(json.load(open("/tmp/swt_create.json")).get("id",""))' 2>/dev/null || true)
echo "created_id: ${ID:-none}"
if [ -z "$ID" ]; then
  echo "verdict: WRITE FAILED (status $CREATE). Plan: mirror off, show our own validated records and the proposal page instead."
  head -c 400 /tmp/swt_create.json; echo; exit 0
fi
echo "--- 2. read back"
READ=$(curl -sS -m 30 -o /tmp/swt_read.json -w '%{http_code}' -H "Accept: application/fhir+json" -H "User-Agent: $UA" "$BASE/Location/$ID")
echo "read_status: $READ"
echo "--- 3. record id in ledger, then delete that id only"
printf '{"ts_utc":"%s","action":"create","resourceType":"Location","id":"%s","purpose":"write-test"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ID" >> "$LEDGER"
DEL=$(curl -sS -m 30 -o /tmp/swt_del.json -w '%{http_code}' -X DELETE -H "User-Agent: $UA" "$BASE/Location/$ID")
echo "delete_status: $DEL"
printf '{"ts_utc":"%s","action":"delete","resourceType":"Location","id":"%s","status":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ID" "$DEL" >> "$LEDGER"
GONE=$(curl -sS -m 30 -o /dev/null -w '%{http_code}' -H "User-Agent: $UA" "$BASE/Location/$ID")
echo "read_after_delete_status: $GONE (410 or 404 means the delete worked)"
if [ "$CREATE" = "201" ]; then echo "verdict: WRITE OK. Mirror as planned."; else echo "verdict: unexpected create status $CREATE, read the output above."; fi
