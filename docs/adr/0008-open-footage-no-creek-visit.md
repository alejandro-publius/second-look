# 0008. No creek visit: the video and the AI use openly licensed footage

- **Status:** accepted
- **Date:** 2026-09-23
- **Carried by:** commit 0ba8a74 (`docs/video/footage.csv`), commit c7e445b (fetch and cut the open
  footage) and commit 8f56355 ("No creek trip: open footage replaced it"); `scripts/fetch_footage.py`,
  `scripts/cut_footage.py`, `docs/video/CREDITS.md`, `scripts/tests/test_no_video_files.py`

## Context

The demo video needed creek shots, and the plan had been for Alex to film at a creek. He was not
going to. The AI evaluation on footage also needed real creek video that we may use.

## Decision

Use openly licensed footage and photos instead, every item CC0, CC BY, CC BY-SA or public domain,
listed in `docs/video/footage.csv`. Each file is downloaded outside the repository, one request a
second with a named user agent, and its licence is checked again on its source page. Every clip
carries a credit line on screen, and every item is credited in `docs/video/CREDITS.md`. Because
several are CC BY-SA, the finished video is released under CC BY-SA 4.0. Nothing says the footage
is our own visit or record, the Strawberry Creek photos are named with their author, and an outfall
is called an outfall. The footage the AI evaluation uses was chosen separately, from openly
licensed videos, and screened frame by frame for people and readable text (`videos/manifest.csv`).

## Consequences

- Video files are never committed, whatever their size; a test checks every tracked file.
- The only video step left for a person is recording the voice over the rough cut.
- The footage result leans on agreement between models, because almost no open description names
  a feature; the README says so under its known weaknesses.
