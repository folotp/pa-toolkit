# pa-toolkit

Pierre-André's personal Claude plugin for Claude Code and Cowork. It holds cross-cutting agents and skills. [`organon-plugin`](https://github.com/folotp/organon-plugin) stays the vault infrastructure (conventions, read/write discipline); this plugin builds on it.

## What it provides

### Agents

- **`decision-gatekeeper`** (sonnet, read-only): before a decision record is written, triages a proposed change against one domain's records and returns one outcome:
  - **(a)** covered by an existing record (quoted);
  - **(b)** new record (working title ≤ 8 words + 2–3 decision drivers, no ID guess — Templater assigns it);
  - **(b′)** supersede an existing record via `Supersede-ADR-template.md`;
  - **(c)** another note type (rule, assumption, runbook, backlog item…);
  - **(d)** operational, proceed.

  It is domain-agnostic. Everything it knows about a domain comes from that domain's **« Profil de gouvernance des décisions »** section in the Organon vault, read fresh on every call. It follows `superseded-by` so it never cites a superseded record, and it stops if a domain has no profile. Current profiles:
  - FIN — `99 - Méta/AI/Claude/Finance Bootstrap.md`
  - SD — `99 - Méta/Système documentaire/ADR/Index — SD-ADR.md`

  **Triggering.** In Cowork, subagents only run on explicit request: « passe ça au gatekeeper », « est-ce que ça mérite une DEC », "run the decision gatekeeper". In Claude Code it may also trigger proactively on policy-shaped proposals.

- **`plugin-release-executor`** (sonnet): the release runbook, dispatched only by the `plugin-release` skill.

### Skills

| Skill | Invocation | Purpose |
| --- | --- | --- |
| `fin-pocketsmith-categorize-amazon` | description-triggered | Categorize/split Amazon transactions from real order contents |
| `fin-pocketsmith-categorize-apple` | description-triggered | Categorize/split APPLE.COM/BILL charges from receipts in Apple Mail |
| `fin-pocketsmith-categorize-netflix` | description-triggered | Split the monthly Netflix charge into its two fixed shares |
| `fin-pocketsmith-categorize-rogers` | description-triggered | Split Rogers wireless charges per line from the invoice |
| `fin-pocketsmith-manage-vacation` | description-triggered | Full vacation lifecycle in PocketSmith (label, categorization, close, Épicerie prorata) |
| `fin-rogers-download-invoice` | description-triggered | Download and archive Rogers invoice PDFs |
| `plugin-release` | user-only: `/pa-toolkit:plugin-release` | Release any of PA's plugins (see below) |

The `fin-*` skills were migrated verbatim from PA's account skills. Their MCP tool names are unprefixed. Several depend on Cowork-only tools and will not run in Claude Code:
- `fin-rogers-download-invoice`: `device_bash`, the `~/mnt` mount;
- `fin-pocketsmith-categorize-rogers`: `device_list_dir`;
- `fin-pocketsmith-categorize-amazon`: the built-in browser.

## Install

```text
/plugin marketplace add folotp/claude-marketplace
/plugin install pa-toolkit@folotp-marketplace
/reload-plugins
```

Each GitHub Release also carries `pa-toolkit-v<version>.plugin` for a direct install in Cowork.

After installing, remove the account-level copies of the `fin-*` skills so they don't trigger twice.

**Requirements.** The Organon MCP must be available on the surface: the claude.ai connector (`mcp__claude_ai_organon__*`) or the organon plugin's server. There is no bundled `.mcp.json`, because a second server would shadow the one the surface already provides. For the same reason `decision-gatekeeper` refers to vault tools by bare name and doesn't pin `tools:`. The `fin-*` skills also need the PocketSmith MCP.

## Adding a domain to the gatekeeper

Write a section titled « Profil de gouvernance des décisions » in that domain's canonical vault note, following the FIN and SD profiles. It should state:
- the decision prefix, folder and index;
- each neighbouring note type and when to choose it;
- what does and does not warrant a decision, with examples;
- the supersession template.

No change to this repo is needed.

## Releasing (any of PA's plugins)

`/pa-toolkit:plugin-release [patch|minor|major|none] [repo-path] [--dry-run]` dispatches `plugin-release-executor`, which:
- reads the plugin name from `.claude-plugin/plugin.json` and the repo from `git remote get-url origin`;
- runs the pre-flight: clean tree, free tag, repo-specific gates from the target's `CLAUDE.md` / `release-readiness`, `plugin-dev:plugin-validator`;
- builds `<name>-v<version>.plugin` with `skills/plugin-release/scripts/package.sh`;
- pushes main before tagging and creates the GitHub Release with `--notes-file`;
- adds the entry to `folotp/claude-marketplace` by PR, or, if the entry already exists, lets the marketplace's auto-bump workflow re-pin it.

Safeguards:
- run a dry-run first;
- never reuse a tag;
- never commit the `.plugin`;
- no `--no-verify`.

This repo does not ship a `notify-marketplace.yml` workflow yet. Without it the marketplace cron picks up new releases within 30 minutes. Adding it needs a `MARKETPLACE_DISPATCH_TOKEN` secret; see the marketplace README.

## Layout

```
.claude-plugin/plugin.json      version source of truth (semver)
agents/                         decision-gatekeeper, plugin-release-executor
skills/fin-*/SKILL.md           six finance skills
skills/plugin-release/          SKILL.md shim, scripts/package.sh, references/release-notes-template.md
```

Tracked in Organon as SD-BL-0066.
