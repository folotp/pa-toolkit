# Supported development agents and CI

The supported development-agent targets are **Codex, Claude Code, GitHub Copilot
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
| Codex CLI/local | `AGENTS.md`; `scripts/dev session codex` | `.codex/hooks.json` requires trusted project/definitions and enabled hooks. No trust or sandbox bypass in test runner | 0.167.2: fresh instruction discovery and native edit bytes pass; no native hook witnesses in isolated probe, hook delivery blocked |
| Claude Code local | `CLAUDE.md` imports `AGENTS.md`; `scripts/dev session claude` | `.claude/settings.json`; native Read/Edit feedback and branch guards. Shell/MCP writes rely on Git/CI | 2.1.322: fresh discovery, native start/edit/feedback/stop, unchanged defect bytes and detached denial pass |
| GitHub Copilot | `AGENTS.md` where supported, otherwise `.github/copilot-instructions.md` points to it; `scripts/dev session copilot` for CLI | Features differ across CLI, IDE, cloud agent and review. No Copilot hook adapter is claimed here; shared commands/Git/CI remain required | Launcher dispatch tested; real CLI unavailable on test host; IDE/cloud not run |
| Google Antigravity | Current rules documentation loads `AGENTS.md`; `scripts/dev session antigravity` invokes `agy` | Installed CLI 1.5.6 is distinct from current documentation; no native hook adapter is claimed. Verify actual version/surface discovery using the plan | Launcher dispatch tested; live client scenarios not run |
| GitHub Actions | Workflow invokes `scripts/dev ci`; complete history and trusted baseline proof | Stable required Linux/macOS contexts; full main/schedule/release and conservative PR reduction. No LLM client/auth needed | Merged #24 main run passes both OSes; follow-up PR must supply current-head results |

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
