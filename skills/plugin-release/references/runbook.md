# Shared plugin release runbook

Agent-neutral source of the release procedure. Publishing requires explicit user authorization; implementation/testing authorizes dry-runs only. Follow these steps in order and stop on failure.

## 0. Resolve identity (read-only)

```bash
cd "<repo root>"
MANIFEST=plugin.json
[ -f "$MANIFEST" ] || MANIFEST=.claude-plugin/plugin.json
NAME=$(jq -r .name "$MANIFEST")
CUR=$(jq -r .version "$MANIFEST")
REPO=$(git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')
MARKET="<explicit marketplace worktree>"
```

Resolve `TOOLKIT_ROOT` explicitly from the selected checkout or installed plugin root. Do not search caches and guess the newest copy. Set `RELEASE_DRIVER="$TOOLKIT_ROOT/skills/plugin-release/scripts/release.py"` and `PKG="$TOOLKIT_ROOT/skills/plugin-release/scripts/package.sh"`. Both paths may be outside a Claude cache. Use Python 3.9+ for the driver; the selected repository may require a newer managed Python. Read canonical AGENTS.md and repository release documentation before proceeding.

Compute `NEW` from `CUR` and the bump (`none` → `NEW=CUR`). Everything below uses `$NAME`, `$REPO`, `$NEW`. Semver: patch = fix/doc; minor = new skill/agent or behavioral rule; major = removed component or breaking description change.

## 1. Pre-flight (all modes)

1. Clean tree: `git status --porcelain` empty. Branch is `main` unless PA named another.
2. `main` is in sync: `git fetch origin && git status -sb` shows no ahead/behind.
3. Tag is free: `git rev-parse -q --verify "refs/tags/v$NEW"` fails **and** `gh release view "v$NEW" -R "$REPO"` fails. A used tag is never reused or overwritten; bump instead.
4. Deterministic validation and packaging run through `release.py` below. A repository may declare `config/release.json` (see the extension contract below); a declared failing/missing check stops execution. With no extension, require any mandatory checks in the repository's tracked release guidance, then use the tracked-file packaging fallback.
5. Claude plugin validation is an optional client compatibility smoke test, separate from mandatory portable checks. Report it as unavailable when the client is absent; never substitute it for mandatory checks.
6. `.gitignore` contains `*.plugin`.

## 2. Dry-run stops here

If `dry-run: true`, create a temporary receipt path and run:

```sh
python3 "$RELEASE_DRIVER" "<repo root>" --packager "$PKG" --output "<explicit output directory>" --dry-run --result "$RESULT"
```

This executes the same preflight and packaging contract as a release build, verifies a real temporary archive, and cleans staging. The JSON receipt contains `planned_archive`; `archive` is null so it cannot accidentally be uploaded. Report identity, proposed bump, planned archive, commit/tag/release commands and marketplace action. Do not commit, tag, push, publish, or dispatch marketplace workflows. Remove the temporary receipt after reading it. Temporary files are the only writes.

## 3. Version bump (skip when bump = none)

Edit only `version` in the canonical `$MANIFEST` with the current client’s edit tool; preserve any Claude manifest symlink. Update the repository’s release entry/changelog when required by its contract. Commit on a `chore/release-v$NEW` branch, open a PR, and stop for PA to merge unless PA said to merge. Releases are tagged only on merged `main` commits.

**Before step 4:** use a dedicated release worktree on `main` (never switch an active development checkout), fetch and fast-forward, confirm `jq -r .version "$MANIFEST"` equals `$NEW`, and re-run pre-flight 1–3. Never build or tag from a release branch: a squash merge would leave the tag off `main` and break the marketplace `sha` pin.

## 4. Build

```sh
python3 "$RELEASE_DRIVER" "<repo root>" --packager "$PKG" --output "<explicit output directory>" --result "$RESULT"
ARCHIVE=$(jq -er '.archive' "$RESULT")
```

Carry this exact verified absolute `ARCHIVE` to upload. Do not assume an archive exists in the repository root. Repeat required gates on the exact merged release commit; earlier branch checks do not verify a squash merge. Keep output and receipt outside tracked source.

## 5. Tag and push (main first)

```bash
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
git tag -a "v$NEW" -m "$NAME v$NEW — <summary>"
git push origin "v$NEW"
```

Require the exact commit to exist on remote main through a merged PR before tagging. Never bypass protected-main rules.

## 6. GitHub Release

Write the body to a temp file under `$TMPDIR` from the template next to `PKG` (`$TOOLKIT_ROOT/skills/plugin-release/references/release-notes-template.md`), or from PA's notes, then:

```bash
gh release create "v$NEW" "$ARCHIVE" -R "$REPO" \
    --title "$NAME v$NEW — <summary>" --notes-file "$NOTES_FILE"
gh release view "v$NEW" -R "$REPO" --json assets --jq '.assets[].name'   # expect $NAME-v$NEW.plugin
```

`--notes-from-tag` is incompatible with `--repo`; always use `--notes-file`.

## 7. Marketplace (`folotp/pa-marketplace`)

The marketplace pins external plugins by `ref` + `sha` and requires public source repos. Use a separate marketplace worktree, fetch and fast-forward; never switch another session’s checkout.

- **No entry named `$NAME`** in `.claude-plugin/marketplace.json`: on branch `feat/add-$NAME`, append an entry shaped like the existing `organon` one — `name`, `source: {"source":"github","repo":"$REPO","ref":"v$NEW","sha":"<git rev-list -n1 v$NEW>"}`, `description`, `category`, `tags` (compact single-line array). No `version` field. Add the README plugins-table row. Run `python3 scripts/validate-marketplace.py`; it must pass. Commit, push, open a PR.
- **Entry exists**: don't hand-edit; the auto-bump workflow re-pins it. Run `gh workflow run auto-bump-external-plugins.yml -R folotp/pa-marketplace`, wait for the run, and inspect the generated bump PR and report its URL. The entry reaches `v$NEW` after that PR merges; do not claim marketplace publication before verifying the merged manifest.

## Report

Return: name, repo, old → new version, tag, Release URL, asset name, marketplace PR URL or bump status, and anything skipped. Never claim a step you did not verify with a command output.

## Anti-patterns

- Committing the `.plugin` archive, or using `--no-verify`.
- Tagging before pushing main; `git tag -f` on a published tag.
- Skipping a required portable check: the marketplace does not replace release validation.
- Editing `marketplace.json` for an existing entry instead of letting auto-bump do it.

## Release notes

Read subjects and bodies from `git log --first-parent <previous-tag>..HEAD`. Include single-parent/squash PR commits as well as merge commits; never filter only `--merges`. Preserve uncategorized changes under Other and use the adjacent release-notes template.

## Repository extension contract

`config/release.json` declares `schema_version: 1`, `preflight` and `package` as nonempty argv arrays. `{packager}` is the explicitly resolved generic package.sh; `{output}` is the driver's temporary absolute output directory. No shell evaluation is performed. The package command must write exactly `<name>-v<version>.plugin` into `{output}`. Preflight and package errors fail both dry-run and build. The extension is executable repository code: review it before running. Organon supplies its shared dev commands; no plugin-specific routing lives here.

Without an extension, packaging snapshots tracked HEAD with `git archive`, excluding ignored/untracked artifacts. Commit release edits before building. The fallback does not replace required repository tests. Source changes do not update installed plugin copies: select this checkout explicitly for development tests, then distribute an authorized release separately.
