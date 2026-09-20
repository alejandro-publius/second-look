#!/usr/bin/env bash
# Build the OneAquaHealth guide at the pinned commit with our FSH inside it (hard rule 11).
# Output: fhir/build/ig/fsh-generated/resources (their profiles plus our examples).
set -euo pipefail
cd "$(dirname "$0")/.."
PIN=$(sed -n 's/^ig_commit: *//p' fhir/ig.lock 2>/dev/null || echo b907cf0)
SUSHI_VERSION=$(sed -n 's/^sushi_version: *//p' fhir/ig.lock 2>/dev/null || echo 3.20.1)
SRC=fhir/ig-src
BUILD=fhir/build/ig
if [ ! -d "$SRC/.git" ]; then
  git clone -q https://github.com/hl7-eu/oah "$SRC"
fi
git -C "$SRC" fetch -q origin 2>/dev/null || true
git -C "$SRC" checkout -q "$PIN"
echo "guide source: hl7-eu/oah at $(git -C "$SRC" rev-parse --short=7 HEAD)"
rm -rf "$BUILD"; mkdir -p "$BUILD"
rsync -a --exclude .git --exclude fsh-generated "$SRC/" "$BUILD/"
mkdir -p "$BUILD/input/fsh/second-look"
cp fhir/fsh/*.fsh "$BUILD/input/fsh/second-look/"
( cd "$BUILD" && npx --yes "fsh-sushi@$SUSHI_VERSION" . 2>&1 | tail -12 )
COUNT=$(ls "$BUILD/fsh-generated/resources" | wc -l | tr -d ' ')
echo "built $COUNT resources into $BUILD/fsh-generated/resources"
