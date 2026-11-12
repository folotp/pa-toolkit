# Supported-agent verification — 2026-11-12

Scope: follow-up to merged #24 / main `18fd53d`, with current feature source exported
by `scripts/verify-agent.py` (including WIP). The
[sanitized event evidence](agent-events.json) records the tested launcher/adapter/
hook hashes, exact client versions, observed outputs and fixture-only observer.
These probes do not certify a later source change or all IDE/cloud variants.

| Surface/scenario | Observed result |
| --- | --- |
| Codex CLI 0.167.2, fresh canonical instruction marker | PASS |
| Codex CLI 0.167.2, exact native shell/JSON fixture edit bytes | PASS |
| Codex CLI 0.167.2, native start/edit/feedback/stop delivery | BLOCKED: no observer records in isolated project probe; hooks enabled, no trust bypass |
| Codex CLI detached native guard / advisory behavior | NOT RUN / NOT PROVEN because required native delivery was not witnessed |
| Claude Code 2.1.322, discovery and exact native fixture edits | PASS |
| Claude Code native start/edit/feedback/stop, bounded non-mutating feedback | PASS; actual event outputs recorded |
| Claude Code detached native edit denial | PASS; exit-2 pre-edit witness and unchanged bytes |
| All four session launcher names, cwd/argument forwarding | Covered by deterministic regression with stand-in executables, not real Copilot/Antigravity acceptance |
| Copilot real-client scenarios | BLOCKED: no Copilot CLI on host; IDE/cloud acceptance NOT RUN |
| Antigravity live-client scenarios | NOT RUN; `agy` CLI 1.5.6 is available, no untested compatibility claimed |

Commands:

```sh
python3 scripts/verify-agent.py --client codex --output /outside/source/codex.json
python3 scripts/verify-agent.py --client claude --output /outside/source/claude.json
./scripts/dev check
./scripts/dev check --staged
```

The client probes use separate disposable repositories, no personal vault/MCP access,
no commits to the selected source and no global trust/sandbox/permission changes.
Only Read/Edit tools are exposed to Claude; Codex uses workspace-write, ignores user
configuration, enables hooks without trusting them and retains normal trust enforcement.
The source hook function is wrapped only inside the fixture for actual event evidence;
raw model streams are not uploaded. Fixture repositories are removed after the test.
The Codex partial result returns nonzero; the runner does not count it as full success.
Earlier bypass-assisted Codex recordings remain historical, not current no-bypass proof.

The reusable [scenario catalogue](../agent-test-plan.md) covers Git/index/CI fallback,
worktree independence, missing prerequisites and release/package contracts using the
existing deterministic fixtures. The current official specification resolver has new
regressions for evolving published versions/current revisions, unavailable/ambiguous
upstream sources, newest-schema requirements and credential-free upstream execution.
Live validation passed locally against the resolved official skills-ref and published
plugin schema; current prose sources are labelled MANUAL_REVIEW, not machine-certified.

The implementation PR's required Linux and macos-15 ARM checks must be read for the
current commit. The workflow also uploads current official-source provenance artifacts.
No model-backed client test is made a required deterministic CI dependency.
