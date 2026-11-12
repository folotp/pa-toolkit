# pa-toolkit development contract

<context>
Repo: folotp/pa-toolkit — PA's personal plugin (agents + skills), separate from organon-plugin, which stays vault infrastructure. Distributed via GitHub Release .plugin asset; consumed by folotp/pa-marketplace. Tracked in vault note SD-BL-0066.
No bundled .mcp.json: vault access uses the Organon MCP each surface already provides (claude.ai connector or organon plugin); bundling another would shadow it. Tool prefixes differ by surface (mcp__claude_ai_organon__*, mcp__organon__*), so agents and skills refer to tools by bare name (search_vault_smart) and don't pin `tools:` to one prefix.
</context>

<design>
decision-gatekeeper is domain-agnostic. Domain knowledge lives in each domain's "Profil de gouvernance des décisions" section in the vault, read fresh on every call; adding a domain means writing its profile, not editing this repo. Keep domain rules out of agents/ so the vault stays the single source of truth.
Finance skills are named fin-<tool>-<action>.
</design>

<workflow>
Version SOT: .claude-plugin/plugin.json (semver). .plugin is gitignored; it exists only as a Release asset.
Release: verify the exact release commit is already merged to remote main before tagging. gh release create: --notes-from-tag is incompatible with --repo; use --notes-file.
</workflow>

<constraints>
Work on a branch (feat/ fix/ chore/ perf/ docs/) and merge by PR rather than committing to main, so release tags always point at reviewed commits.
</constraints>

## Code and documentation

Code must explain its own intent through precise names, coherent functions and explicit contracts. Add docstrings or nearby comments for non-obvious inputs/outputs, side effects, failure behavior, invariants and the reasons behind important decisions; do not narrate obvious statements. Complement the code with repository architecture/design documents and operational runbooks. Update code, related docs, examples and tests together in the same PR. Preserve one authoritative implementation of each policy; client adapters refer to it. Documentation is part of completion, not a later task. A reviewer must be able to understand, operate and modify the change without this conversation or private agent memory.

## Shared release infrastructure

Read `skills/plugin-release/references/development.md` for architecture, extension/receipt contracts, tests and CI. The canonical general release procedure is `skills/plugin-release/references/runbook.md`; the Claude executor is an adapter. Run `python3 -m unittest discover -s tests -v` before committing release infrastructure changes. Use one named branch/worktree per editing agent and merge through a PR. Do not publish, tag or change marketplace pins without an authorized release request.

## Shared development interface

Use `./scripts/dev doctor`, `./scripts/dev check` and `./scripts/dev check --staged`.
Run the full gate before committing; Git validates the actual index separately.
`./scripts/dev format` is an explicit source write. Lifecycle feedback never formats.
Create worktrees with `./scripts/dev worktree feat/example /explicit/path`; start
Claude/Codex with `./scripts/dev session claude|codex` from that checkout, including
when invoking the launcher from a subdirectory. Preserve other sessions' checkouts.

Development uses locked Python dependencies (`uv sync --locked`), Bash 3.2-compatible
shell code and the supported tools in `config/toolchain.json`. Launcher Python 3.9+
and managed project Python 3.11-3.15 are distinct. No development gate needs a vault,
finance service, installed AI client or installed Git hook. Missing required tools,
blocked caches/network and unavailable checks fail with a setup remedy.

Architecture, setup, CI ownership, client limits and recovery are maintained in the
[development architecture](https://github.com/folotp/pa-toolkit/blob/main/docs/development-architecture.md),
[development runbook](https://github.com/folotp/pa-toolkit/blob/main/docs/development.md)
and [hook scope](https://github.com/folotp/pa-toolkit/blob/main/docs/hook-scope.md).
Maintain source contracts, tests and these documents in the same PR.

`./scripts/dev install-hooks` preflights pre-commit/pre-push, honors `core.hooksPath`
and upgrades only exact recognized toolkit launchers. Shared hook installation
also affects linked worktrees: older branches without the shared launcher fail
closed. Preserve unmanaged hooks and compose manually using the development runbook.
Do not install from a transient checkout without understanding that shared scope.

Runtime files are explicitly selected by `config/package-files.json`. Update this
inventory with runtime additions and verify a real archive through the generic
release driver from a clean worktree. This repository's `config/release.json` selects
its shared full gate and runtime package command. The general runbook/driver remains
the only release implementation; require exact merged remote-main identity again
before an authorized tag. Development adapters/configuration/environments never ship.
