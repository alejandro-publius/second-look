# Locale drafts

`es.json` is an UNVERIFIED machine draft of the Latin American Spanish locale, made on 2026-09-22. It has the same keys as `content/locales/en.json`, in the same order, plus a first `_status` key saying it is unverified.

Nothing reads this folder. The web build, the API and the checks read `content/locales/en.json` by name and never look in `drafts/`.

To sign it, Alex:

1. Reads every string, the `consent.*` strings and every health or safety sentence first.
2. Fixes any string that is wrong, unclear or softer than the English.
3. Moves the file to `content/locales/es.json`, deletes the `_status` line and adds a `"signed_by"` line with his name and the date.

Moving the file does not switch Spanish on. The app still loads only `en.json` until code is added to load `es.json`.
