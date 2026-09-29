---
name: plugin-release
description: Cut a release of any of PA's Claude plugins (pa-toolkit, organon, …) — version bump in `.claude-plugin/plugin.json`, `.plugin` archive, tag, GitHub Release with the asset, and the `folotp/claude-marketplace` entry. User-only (`/pa-toolkit:plugin-release`). Plugin name comes from `plugin.json`, repo from `git remote get-url origin`; nothing is hardcoded. Dispatches to the `plugin-release-executor` agent.
argument-hint: "[patch|minor|major|none] [repo-path] [--dry-run]"
disable-model-invocation: true
allowed-tools:
  - Agent
---

# plugin-release

Routing shim. Its only action is to dispatch the `pa-toolkit:plugin-release-executor` sub-agent, which holds the one and only copy of the release runbook (`agents/plugin-release-executor.md` in pa-toolkit). A release pushes tags and publishes a GitHub Release, so it always goes through the executor, never inline.

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

- `scripts/package.sh <repo-root> [--dry]` — builds `<name>-v<version>.plugin` at the repo root.
- `references/release-notes-template.md` — Release body template.
