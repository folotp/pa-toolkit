# Supported development agents and CI

Supported targets are **Codex, Claude Code, GitHub Copilot on GitHub.com and Google
Antigravity**. GitHub Actions supplies deterministic validation. Support means a
shared repository contract and validation route; native coverage differs by client,
version and surface. The [accepted coverage and limits](acceptance.md) records the
completed implementation's evidence without claiming universal native parity.

`AGENTS.md` is authoritative. Root `CLAUDE.md` is a separate regular file importing
`@AGENTS.md`. `.github/copilot-instructions.md` points to the same policy for hosted
Copilot surfaces. Antigravity uses `AGENTS.md`; this repo has no duplicate `GEMINI.md`.
Client adapters and configuration are development-only and excluded from runtime.

| Surface | Discovery and launch | Integration and operational limits |
| --- | --- | --- |
| Codex local | `AGENTS.md`; `scripts/dev session codex` | Project hooks require supported trust/review. Linked roots can select primary definitions; inspect selected bindings. Shell/MCP and unverified surfaces retain Git/index/CI enforcement |
| Claude Code local | `CLAUDE.md` imports `AGENTS.md`; `scripts/dev session claude` | Project Edit/Write hooks provide branch/path checks and advisory diagnostics; Git/index/CI remain required |
| Claude Code cloud through desktop/web | Actual cloud checkout and startup instruction context | Local CLI results do not certify cloud. Each clone needs its own reviewed Git-hook setup; receipt tracing must reach the parent client before startup |
| GitHub Copilot on GitHub.com | `AGENTS.md` and `.github/copilot-instructions.md` | Hosted cloud agent and PR code review only; no Mac CLI installation or local native-hook parity required |
| Antigravity CLI | `AGENTS.md`; `scripts/dev session antigravity` invokes `agy` | Selected CLI target has no native hook adapter; explicit checks and Git/CI enforce committed changes |
| GitHub Actions | `scripts/dev ci` | Both required Linux/macOS contexts; full main/scheduled/manual/release validation and conservative PR reduction; no LLM credentials required |

Use `scripts/dev doctor`, `scripts/dev check` and actual-index checking regardless of
editing client. The launcher normalizes its child cwd and forwards arguments. It
does not install clients, grant trust/permissions or switch another checkout's branch.
Run one session per worktree. Review shared hook destinations before installation;
see the [cloud setup route](development.md#claude-code-cloud-setup) and [hook scope](hook-scope.md).

A configured adapter is not proof of native delivery. Use the
[reusable acceptance plan](agent-test-plan.md), exact source/harness hashes, actual
native calls/responses and preserved bytes. Missing authentication, entitlement,
review or startup telemetry is an explicit limitation, not a passing test. Owner
acceptance can complete an implementation with those limitations documented.

## Official discovery and lifecycle references

These are authority links, not claims of current version-wide certification. Recheck
the relevant surface when changing integration behavior:

- [Codex hooks and trust](https://learn.chatgpt.com/docs/hooks)
- [Codex noninteractive commands](https://learn.chatgpt.com/docs/developer-commands)
- [Claude hooks](https://code.claude.com/docs/en/hooks)
- [Copilot instruction types and surface differences](https://docs.github.com/en/copilot/concepts/prompting-and-context/custom-instructions)
- [Antigravity rules](https://antigravity.google/docs/rules/)
- [AGENTS.md](https://agents.md/)

## Consumer rollout

Marketplace, Organon and HA configuration adopt this tooling in separately reviewed
repository-specific changes. Keep each consumer's domain gates, credentials and
live-operation boundaries. Shared acceptance mechanics can be referenced; client
results and CI statuses from one repository do not certify another.
