---
name: plugin-release
description: Cut a release of any of PA's Claude plugins (pa-toolkit, organon, …) — version bump in canonical `plugin.json` (legacy Claude manifest fallback), `.plugin` archive, tag, GitHub Release with the asset, and the `folotp/pa-marketplace` entry. User-only (`/pa-toolkit:plugin-release`). Plugin name comes from `plugin.json`, repo from `git remote get-url origin`; nothing is hardcoded. Dispatches to the `plugin-release-executor` agent.
argument-hint: "[patch|minor|major|none] [repo-path] [--dry-run]"
disable-model-invocation: true
allowed-tools:
  - Agent
  - Bash
  - Read
---

# plugin-release

The shared procedure is [references/runbook.md](references/runbook.md); deterministic preflight/build operations are in `scripts/release.py`. Run only when explicitly requested by the user. Publishing still needs explicit authorization.

On Claude, dispatch the thin executor below. On Codex or another agent without `Agent`, read the same runbook and execute it directly, using an explicit pa-toolkit checkout/root. No Claude sub-agent or plugin-validator is a mandatory portable dependency. In either route the driver automatically selects the target repository's extension for both dry-run and build.

## How to dispatch

Parse `$ARGUMENTS`, fill the defaults below, then:

```js
Agent({
  description: "Execute plugin release",
  subagent_type: "pa-toolkit:plugin-release-executor",
  prompt: "bump: <patch|minor|major|none>, repo root: <absolute path>, release notes: <maintainer notes or blank>, dry-run: <true|false>"
})
```

## Args to forward

- **Bump**: `patch`, `minor`, `major`, or `none` (release the version already in `plugin.json`, e.g. a first release). Default: ask PA; never guess a bump.
- **Repo root**: absolute path of the plugin repo to release. Default: the current working directory's git toplevel. The executor reads the plugin name and GitHub repo from there.
- **Release notes**: PA's notes for the Release body; blank → the executor drafts from `references/release-notes-template.md` and the commits since the last tag.
- **Dry-run**: `true` = pre-flight, packaging listing and a printout of every command and marketplace change it would make; nothing is committed, tagged, pushed or published. Default to a dry-run first on any repo that has not been released with this skill before.

## Resources

- `scripts/release.py <repo-root> --output <directory> --result <receipt.json> [--dry-run] [--packager <path>]` — portable preflight and verified archive contract.
- `scripts/package.sh` — low-level generic archive implementation; release callers use the driver.
- `references/release-notes-template.md` — Release body template.
