# Submission checklist

Two lists. The first is what `make submit-check` (scripts/submit_check.py) proves by itself.
The second is what a person must do and tick by hand. Submit only when both are done.
Deadline: Wednesday Sep 30, 2026, 18:00 PDT. Repo public first, then the incognito check.

## Checked by `make submit-check`

| Check | What passes | Today |
|---|---|---|
| track_statement | The first line of README.md equals docs/track_statement.md word for word | pass |
| five_headers | README.md has the organizers' five headers in order: The problem; How the solution aligns with OneAquaHealth; Innovation and practical value; Effective use of data, technology, AI, APIs and standards; A clear demonstration of what was built | pass |
| video_link | A line with the word "video" and a link exists in README.md and docs/devpost.md | fails until the video is uploaded |
| video_duration | With `--video path.mp4`, ffprobe says 180 to 300 seconds; skipped with a sentence when no file is given | skipped |
| license | LICENSE exists and says MIT | pass |
| demo_url | The URL in NEXT_PUBLIC_SITE_URL, or the demo link in docs/devpost.md, answers 200; skipped with a sentence when unset | skipped until deployed |
| secrets_scan | No key shapes (AWS, Anthropic, OpenAI, GitHub, Slack, Google, private key blocks, quoted assigned secrets) in tracked or untracked files; gitleaks over the history when installed | pass |
| verify_claims | `scripts/verify_claims.py` without `--synthetic` passes: every README number traces to a real results file | fails while results are synthetic |
| audit_log | `audit/log.jsonl` chain verifies | pass |
| repo_public | `gh repo view --json visibility` says PUBLIC | fails until Sep 30 |

Expected failures before submission day: video_link, repo_public, verify_claims (real results).
Anything else failing is our fault and gets fixed first.

## Done by a person

- [ ] Video recorded to docs/video_script.md, edited to 3 to 5 minutes (target 3:45), uploaded,
      link pasted into README.md and docs/devpost.md, and `make submit-check --video` run on the file.
- [ ] Devpost page filled: every field in docs/notes/devpost_fields.md mapped to a README section
      in docs/devpost.md, the track statement first, the five headers in order.
- [ ] Demo deployed and awake: the landing page paints without the API; `make smoke` passes
      against the public URL; the API does not sleep (scheduled ping or a host that stays up).
- [ ] Repo made public on Sep 30, then `make submit-check` rerun and fully green.
- [ ] Incognito check on a phone: landing, `/t` both arms, `/demo`, `/check`, `/spot/[id]`,
      View as FHIR, `/two`. No login wall, no console errors, no request to a third-party origin.
- [ ] README first screen: the one sentence, the two warm-up photos, the results table with the
      number of people, the last audit hash from `scripts/verify_audit.py`, and the plan tag.
      Every number came from results/ through verify_claims. No hand-edited numbers.
- [ ] docs/deviations.md: every change after `prereg-v1` is listed with a date and reason, and
      the README shows the deviation count.
- [ ] Nobody is filmed: the creek shots are open footage, each with its credit line on screen and
      in docs/video/CREDITS.md, and the video's description says it is CC BY-SA 4.0. If a person
      ever is filmed, they sign docs/release_form.md first.
- [ ] docs/THIRD_PARTY.md regenerated (`uv run python scripts/third_party.py`) and the licenses
      it could not find checked by hand.
- [ ] `make check` green on main; CI green; no em or en dashes (`scripts/check_dashes.py`).
- [ ] The data lock passed (2026-09-28T01:00:00Z), the analysis ran once, and the anonymous
      response table is published beside the results.
- [ ] Alex posted the last audit hash publicly (the README prints it at freeze).
- [ ] Waiver and consent: the organizers' participation waiver or terms accepted on Devpost by
      Alex; the study consent text still matches docs/DATA_HANDLING.md.
- [ ] Nothing in the repo names a participant, an email, an address or a secret. `.env` is not
      tracked. ANTHROPIC_API_KEY is not in any committed file.
