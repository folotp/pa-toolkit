# Supported development agents and CI

The supported development-agent targets are **Codex, Claude Code, GitHub Copilot on GitHub.com
and Google Antigravity**. **GitHub Actions CI** supplies deterministic validation.
Support means a common repository contract, discovery route and validation workflow;
it does not mean every IDE/cloud variant has identical native hooks or has passed
live acceptance. Evidence is recorded per client/surface/version and scenario.

`AGENTS.md` is authoritative. `CLAUDE.md` is a separate regular file importing
`@AGENTS.md`, with no duplicated policy. `.github/copilot-instructions.md` points
to the shared contract for Copilot surfaces that do not load agent files. Current
Antigravity documentation supports `AGENTS.md` directly; no redundant `GEMINI.md`
is needed. Client configuration is development-only and excluded from runtime.

| Surface | Discovery and launch | Native integration and limits | Current evidence |
| --- | --- | --- | --- |
| Codex CLI/local | `AGENTS.md`; `scripts/dev session codex` | `.codex/hooks.json` requires trusted project/definitions and enabled hooks. No trust or sandbox bypass in test runner | 0.167.2: ordinary trusted linked-root/subdirectory native delivery, diagnostics, detached denial and concurrency pass; independent ignored-config and main-native proof remain blocked |
| Claude Code local | `CLAUDE.md` imports `AGENTS.md`; `scripts/dev session claude` | `.claude/settings.json`; native Read/Edit feedback and branch guards. Shell/MCP writes rely on Git/CI | 2.1.322: strengthened CLI suite passes root/subdirectory discovery, valid/defect edits, successful events, both diagnostics, main and detached denial; interactive/Desktop not certified |
| GitHub Copilot on GitHub.com | Cloud agent and PR code review use `AGENTS.md` plus `.github/copilot-instructions.md` | GitHub-hosted checkout/review and required CI; no local Mac client, session launcher or local hook parity required | Hosted task creation returns 403; PR #30 review API returns 422 ACTOR_INELIGIBLE with no actual review observed; Mac CLI is NOT APPLICABLE |
| Google Antigravity | Current rules documentation loads `AGENTS.md`; `scripts/dev session antigravity` invokes `agy` | PA selected CLI only (2026-11-12); installed 1.5.7; no native hook adapter is configured | CLI smoke plus root/subdirectory concurrent linked edits pass with actual read_file/edit_file events; App/IDE outside selected scope |
| GitHub Actions | Workflow invokes `scripts/dev ci`; complete history and trusted baseline proof | Stable required Linux/macOS contexts; full main/schedule/release and conservative PR reduction. No LLM client/auth needed | Merged #30 exact-main run 43298112159 at 5b5fe08 passes both OSes with 86 tests, live specifications and actual archive; subsequent PRs require their own current-head results |

Antigravity's selected CLI-only scope does not restrict Codex or Claude Code. Their
app/IDE/interactive/hosted scenarios require explicit surface selection and actual
evidence; implemented CLI suites are partial acceptance. See the
[surface matrix](verification/acceptance-surfaces-2026-11-12.md).

Run `scripts/dev doctor` and the full/index commands regardless of the editing
client. The launcher normalizes only its child cwd and forwards arguments; it does
not install clients, grant permissions, trust hooks, or switch the caller's branch.
Copilot/Antigravity native event integration is outside this first implementation;
explicit shared checks and Git/CI are their current enforcement path.

The [reusable acceptance plan](agent-test-plan.md) distinguishes a configured
adapter from native delivery, observed pass from unavailable tests, and client
claims from actual file/event evidence. The current
[verification report](verification/supported-agents.md) records results and blockers.

## Official discovery and lifecycle references

Checked 2026-11-12; changes require per-surface review, not an assumption of parity:

- [Codex hooks and trust](https://learn.chatgpt.com/docs/hooks)
- [Codex noninteractive commands](https://learn.chatgpt.com/docs/developer-commands)
- [Claude hooks](https://code.claude.com/docs/en/hooks)
- [Copilot instruction types and surface differences](https://docs.github.com/en/copilot/concepts/prompting-and-context/custom-instructions)
- [Antigravity rules and AGENTS.md discovery](https://antigravity.google/docs/rules/)
- [AGENTS.md authority](https://agents.md/)

## Cross-repository rollout

This is the first implementation for the expanded scope in toolkit #23. Marketplace
#13, Organon #137 and HA configuration #1087 carry the same four-client support and
live-authoritative-spec requirements. Their implementations remain separate changes;
HA's existing ADR, deployment and live-operation boundaries still govern. No related
repository, marketplace pin or household state is changed by testing this toolkit.

## Testing an unmerged PR

Merge is not a prerequisite for acceptance tests. The runner exports the selected
feature worktree's actual tracked/nonignored bytes into an independent repository.
`source_base_commit` identifies the checkout base, `source_dirty` identifies WIP,
and `source_tree_sha256`/per-file hashes identify the bytes tested. A base SHA alone
must never be represented as proof of the tested PR head or an installed release.
The disposable observer is explicitly labelled and production discovery/configuration
must still be tested separately on the intended real surface.

Current continuation: [2026-11-12 CLI acceptance](verification/acceptance-cli-2026-11-12.md), including actual native events, source hashes and exact access blockers.
