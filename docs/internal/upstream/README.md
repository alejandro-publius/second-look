# Contribution to hl7-eu/oah, ready for when our repo is public

Our FSH example and the pull request text for the OneAquaHealth implementation guide. Open it only after `make go-public GO=yes` on Sep 30, because the pull request links to our repository.

- The FSH is `fhir/fsh/*.fsh` in this repository, the files CI builds and validates. There is no copy here: pull request #5 carried a snapshot, and it was the same, byte for byte, as `fhir/fsh/` on 2026-09-23. Step 3 below copies the files fresh.
- `PR_BODY.md`: the title on its first line, then the body. Shortened from `docs/ig_proposal.md`.

## Commands (on the Mac, about 10 minutes)

1. Fork and clone, with the GitHub CLI:

```bash
cd ~ && gh repo fork hl7-eu/oah --clone --remote && cd oah
git fetch upstream && git checkout -b second-look-citizen-observer upstream/master
```

If their default branch is `main`, use `upstream/main`. Check with `gh repo view hl7-eu/oah --json defaultBranchRef`.

2. Our example was built against b907cf0. See what changed since:

```bash
git log --oneline b907cf0..HEAD | head -20
```

If profiles we use changed (`LocationOah`, `ObservationIndicatorsOah`), run step 4 before opening anything.

3. Copy the FSH in, fresh from our repo:

```bash
mkdir -p input/fsh/second-look
cp ~/second-look-depth/fhir/fsh/*.fsh input/fsh/second-look/
```

4. Build with the same SUSHI we pin:

```bash
npx --yes fsh-sushi@3.20.1 . 2>&1 | tail -5
```

It must say 0 errors. If it does not, stop and bring the output back to a session.

5. Commit, push and open the pull request:

```bash
git add input/fsh/second-look
git commit -m "Example: a citizen observer's test score carried with their observations"
git push -u origin second-look-citizen-observer
gh pr create --repo hl7-eu/oah --title "$(head -1 ~/second-look-depth/docs/internal/upstream/PR_BODY.md | sed 's/^Title: //')" --body "$(tail -n +3 ~/second-look-depth/docs/internal/upstream/PR_BODY.md)"
```

6. Put the pull request link in the README under "Contributed back" and in the status issue.

Rules that still hold: never call `api.enora-oah.eu`; this touches only their public GitHub repository.
