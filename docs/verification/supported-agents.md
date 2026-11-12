# Supported-agent verification — 2026-11-12

Scope: **unmerged PR #29**, tested by exporting its feature-worktree bytes into
independent disposable repositories. The refreshed Claude probe uses base `28014f6`
plus the review-correction WIP. `source_base_commit` is the checkout base, not a claim
that main or that exact clean commit was tested; tree/per-file hashes identify bytes.
The Codex result is explicitly historical pre-28014f6 WIP, not rerun for this correction. The
[sanitized event evidence](agent-events.json) records the tested launcher/adapter/
hook hashes, exact client versions, observed outputs and fixture-only observer.
These probes do not certify a later source change or all IDE/cloud variants.

| Surface/scenario | Observed result |
| --- | --- |
| Codex CLI 0.167.2, fresh canonical instruction marker | PASS |
| Codex CLI 0.167.2, exact native shell/JSON fixture edit bytes | PASS |
| Codex CLI 0.167.2, native start/edit/feedback/stop delivery | BLOCKED: no observer records in isolated project probe; hooks enabled, no trust bypass |
| Codex CLI detached native guard / advisory behavior | NOT RUN / NOT PROVEN because required native delivery was not witnessed |
| Claude Code 2.1.322, root discovery/valid edit and subdirectory defect edits | PASS |
| Claude Code native start/edit/feedback/stop, successful exits and both path-specific diagnostics | PASS; shell diff and JSON parse defect both observed; bytes remain intact |
| Claude Code detached and main native edit denial | PASS; exit-2 pre-edit witnesses and unchanged bytes |
| Three local session launcher names, cwd/argument forwarding | Codex/Claude/Antigravity dispatch covered by deterministic regressions |
| Copilot on GitHub.com cloud-agent/code-review acceptance | NOT RUN; local Mac client is NOT APPLICABLE, not a blocker |
| Antigravity CLI 1.5.7 | PASS: discovery, valid/text/multi-file edits, actual read_file/edit_file events; App/IDE and native hooks not certified |

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

## Review correction and coverage limits

PR review identified that the earlier overall PASS predicate only required event
names and edited bytes. It could falsely pass missing diagnostics. The runner now
preflights diagnostic prerequisites, requires exit-zero positive hooks, identifies
feedback paths, and asserts both the exact shell diff and JSON parse diagnostic.
Missing tools return BLOCKED with a remedy; missing defect detection returns FAIL.
Six focused regressions cover these cases; a seventh requires actual Antigravity
edit-tool evidence. The suite now has 73 tests.

Fresh Claude CLI tests pass the strengthened checks plus root valid edits and both
main/detached denials. This is the implemented automated CLI acceptance suite, **not**
the entire catalogue across interactive/Desktop/IDE/cloud surfaces. G/E/S/P cases are
separate deterministic fixtures, not proof of every workflow executed by Claude.
A separate human Claude session is unnecessary to repeat the automated CLI scenarios;
interactive product behavior requires its own evidence if made a support requirement.

Copilot support now explicitly targets GitHub.com cloud agent and PR code review.
The Mac CLI dispatcher and its acceptance requirement were removed. GitHub Actions
results are not represented as Copilot-model behavior tests.

Antigravity CLI 1.5.7 was executed twice successfully in independent fixtures with
its sandbox enabled. The retained run proves instruction-marker discovery, exact
valid text/shell/JSON edit bytes, and actual `read_file` / `edit_file` events. No shell
write was used in that run. This is a CLI smoke test, not full Antigravity product
acceptance: no Antigravity native hook adapter exists here, and App/IDE, concurrency,
main/detached native guards and hosted/remote modes are not certified by it.
