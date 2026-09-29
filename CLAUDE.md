<context>
Repo: folotp/pa-toolkit — PA's personal plugin (agents + skills), separate from organon-plugin, which stays vault infrastructure. Distributed via GitHub Release .plugin asset; consumed by folotp/claude-marketplace. Tracked in vault note SD-BL-0066.
No bundled .mcp.json: vault access uses the Organon MCP each surface already provides (claude.ai connector or organon plugin); bundling another would shadow it. Tool prefixes differ by surface (mcp__claude_ai_organon__*, mcp__organon__*), so agents and skills refer to tools by bare name (search_vault_smart) and don't pin `tools:` to one prefix.
</context>

<design>
decision-gatekeeper is domain-agnostic. Domain knowledge lives in each domain's "Profil de gouvernance des décisions" section in the vault, read fresh on every call; adding a domain means writing its profile, not editing this repo. Keep domain rules out of agents/ so the vault stays the single source of truth.
Finance skills are named fin-<tool>-<action>.
</design>

<workflow>
Version SOT: .claude-plugin/plugin.json (semver). .plugin is gitignored; it exists only as a Release asset.
Release: push main before tagging. gh release create: --notes-from-tag is incompatible with --repo; use --notes-file.
</workflow>

<constraints>
Work on a branch (feat/ fix/ chore/ perf/ docs/) and merge by PR rather than committing to main, so release tags always point at reviewed commits.
</constraints>
