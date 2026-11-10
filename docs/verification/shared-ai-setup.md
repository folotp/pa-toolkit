# Agent-neutral development verification

Date: 2026-11-10 (America/Toronto). Issue: [#23](https://github.com/folotp/pa-toolkit/issues/23).
Implementation PR: [#24](https://github.com/folotp/pa-toolkit/pull/24).
Starting toolkit main: `6eee6183bed5f8e8221541afbd516f551d718a4f`.
Read-only Organon reference: `c5a9cd8fabd2af5459ea073850204caa70ae9ad7`.
Initial implementation: `4c72eb7a47c347c01e2a6badb84d0511f93bb147`; acceptance-driven
hardening follows in the same feature branch. This is development acceptance, not a
release. No personal vault, financial operation, marketplace change or publication
was used. Global trust/permission settings were not changed.

## Starting state and isolation

Fetched origin and confirmed local main matched remote main. The primary toolkit
checkout was clean, with one initial worktree and generic managed pre-commit and
pre-push launchers pointing at stable toolkit main. `core.hooksPath` was unset.
Live main protection required PRs, strict `Release checks (ubuntu-latest)` and
`Release checks (macos-latest)`, with admin enforcement and no force pushes/deletion.
No server settings were changed. Organon was clean on its recorded main commit and
was used only for read-only source/documentation inspection.

After fixture verification, `scripts/dev install-hooks` upgraded both exact recognized
local generic guards to the worktree-resolving v1 launchers. The acceptance commit
runs the installed full staged gate; the branch push runs its destination guard.
No unmanaged hook was replaced, and no transient source path is retained. Older
branches without scripts/dev fail closed until updated, as documented in recovery.

Created `feat/agent-neutral-development` at `/private/tmp/pa-toolkit-agent-neutral`
before editing. Independent disposable linked worktrees were used for Claude,
Codex, archive integration and real index tests, each with its own branch except
for the detached archive checkout. Client fixtures appended a unique instruction
marker to AGENTS.md and added only synthetic smoke.sh/smoke.json. No runtime skill
was executed against a vault or account. Only the controller switched the fixture
checkouts to detached HEAD for expected-denial tests; clients never changed branches.
Primary checkouts were checked before/after for branch, HEAD and status independence.

## Toolchain and deterministic gates

Observed macOS tools: Git 2.54.0, uv 0.13.7, Bash 3.2.57, jq 1.7.1, Zip 3.0,
UnZip 6.0, shfmt 3.14.1, ShellCheck 0.11.0 and actionlint 1.7.12. Full checks used
managed CPython 3.11.18. Launcher Python 3.9 was probed independently with
`/usr/bin/python3 scripts/dev.py doctor`; it successfully diagnosed the separate
managed interpreter and imports. Project Python libraries are pinned/hash locked.

`./scripts/dev check` and `./scripts/dev check --staged` run the same complete gate.
The regression suite has 44 tests, including existing extension/fallback and brace
contracts plus index isolation, real parser failures, staged additions/deletions/modes,
inherited Git-variable isolation, unmerged/main/detached denial, unmanaged/custom/shared
hooks, exact legacy migration, symlink preservation, component schemas, package bytes,
malformed configuration, missing/old tools and blocked managed-environment diagnostics.
The existing generic release driver remains stdlib-only and Python 3.9 compatible.

The first uv operation was blocked by sandbox access to its existing cache and failed
with a setup remedy. Approved cache access allowed locked sync/checks to pass; no
required check was skipped. Expected negative-test stderr (invalid Python, YAML or
unmerged index) is part of the tests and does not indicate an ignored failed gate.
All source shell/Python files were formatted explicitly, including legacy generic
release code, rather than excluding existing formatting defects.

The real full staged acceptance used a separate linked worktree:

1. Replaced the agent description with `description: invalid: staged`, staged it,
   then restored valid working-tree bytes without touching the index.
2. `scripts/dev check --staged` failed with strict YAML's mapping-values error from
   the temporary exported repository. An unstaged repair did not mask the defect.
3. Restored the valid index, introduced the invalid description only in the working
   tree, then reran the same staged command. The full gate and suite passed.

Unit fixtures also verify the original source index/working-tree bytes are preserved
and the exported repo uses its own Git metadata. Guard loading avoids writing Python
bytecode into the selected checkout during lightweight lifecycle/index operations.

## Real archive and release-driver compatibility

From a clean linked checkout, ran both modes of the actual driver:

```sh
python3 skills/plugin-release/scripts/release.py . \
  --dry-run --output /private/tmp/pa-toolkit-acceptance/package \
  --result /private/tmp/pa-toolkit-acceptance/dry-run.json
python3 skills/plugin-release/scripts/release.py . \
  --output /private/tmp/pa-toolkit-acceptance/package \
  --result /private/tmp/pa-toolkit-acceptance/build.json
```

Both selected `config/release.json`, ran the full shared check once and verified a
real archive. The retained `pa-toolkit-v0.1.4.plugin` contained exactly **18 runtime
files / 30 ZIP entries**. Independent ZIP inspection confirmed allowlist equality,
all source bytes and the unchanged legacy manifest identity. Required skills, agents,
release scripts and runbook/reference resources remained. Development hooks/config,
managed environments, tests, CI, build output and arbitrary local files were absent.

The first dry-run attempt completed archive verification but failed to write its
receipt because the explicit receipt parent directory had not been created. Creating
that caller-selected directory and rerunning succeeded. No stale success receipt was
used; a CLI regression also verifies old receipts are removed before required failures.
Dry-run's receipt had null `archive` and an explicit planned path; build's receipt
had the verified absolute retained path. No uploader, tag or release command ran.

`claude plugin validate` passed for both source and extracted runtime payload. The
client separately reported existing directory-submission license/icon issues; these
are optional directory-profile concerns, not errors under the current compatibility
profile. No license was invented or public directory submission attempted. Runtime
payload had no root CLAUDE.md context warning because that development adapter does
not ship. Generic fallback, both modes, literal braces, explicit receipts and malformed
extension failures retain regression tests. Exact merged remote-main verification
before publication remains in the unchanged shared release runbook.

## Fresh Claude and Codex sessions

Clients: **Claude Code 2.1.322**, **Codex CLI 0.167.0**. Each used its own disposable
linked worktree. All client launches originated from that checkout's `scripts/`
subdirectory through `scripts/dev session`; the actual event payload cwd and SessionStart
root were the checkout root. Both reported their unique loaded instruction marker
without opening AGENTS.md or CLAUDE.md. This establishes instruction discovery,
subdirectory normalization and checkout independence for the tested launcher path.

| Surface | Instructions | SessionStart | Native edit feedback | Detached edit denial | Stop |
| --- | --- | --- | --- | --- | --- |
| Claude project settings | Pass | Observed | Edit: shfmt diff and JSON parse error | Exit 2, bytes unchanged | Advisory systemMessage, exit 0 |
| Codex ordinary linked-worktree discovery | Pass | No toolkit feedback delivered | Not claimed | Not claimed | Not claimed |
| Codex reviewed invocation-local definitions | Pass | Observed | One two-file apply_patch: both diagnostics | Exit 2, bytes unchanged | Advisory systemMessage, exit 0 |

Claude's first run used the exact project definitions, project-only settings and no
MCP servers. Its stream recorded SessionStart success and Stop advice; the model
received PostToolUse formatting/JSON feedback. A second instrumentation pass recorded
all four actual events. The fixture-only recorder forwards stdin/stdout/stderr and
exit status unchanged to the shared hook implementation; it is not production code.
Sanitized observed events are retained in [client-hooks.json](client-hooks.json).
The final positive/denial recordings include matching SHA-256 fingerprints of the
shared development implementation and generic branch guard.

For both clients, the positive test deliberately left:

```sh
#!/usr/bin/env bash
if true;then echo after;fi
```

and invalid JSON `{"invalid":}`. File inspection confirmed both defects remained.
Feedback explicitly said files were unchanged, labeled shfmt versus ShellCheck, and
reported JSON's expected-value error. Stop ran once per completed test, returned
advisory JSON and did not request another turn. Negative tests on detached HEAD tried
one native edit, received exit 2 and respected the denial without another editing
path. Controller inspection verified the proposed `echo denied` never reached disk.

Codex default linked-worktree discovery did not deliver toolkit hooks; this is a real
limitation, not a successful hook test. Explicit invocation-local hook arrays selected
the reviewed fixture definitions and `--dangerously-bypass-hook-trust` permitted only
those vetted definitions for the test invocation. `-s workspace-write` remained enabled;
no global trust/project settings were changed. Ordinary users should inspect/review
`/hooks`; after merge update primary main so discovery sees the tracked definitions.
External follow-up is Codex per-worktree hook discovery, not a toolkit engine change.

The current Codex code-mode host exposes native patching through `functions.exec`.
An initial test prohibited nested invocation and therefore made no edit. Disabling
the code-mode host also made tools unavailable; this was not treated as a passing
edit test. Allowing `tools.apply_patch` through the normal code-mode host produced
canonical `tool_name: apply_patch` PreToolUse/PostToolUse events for a real **single
two-file patch**, including both paths in `tool_input.command`. Thus this specific
nested native path is verified. Arbitrary shell/MCP/other nested/hosted writes remain
outside the demonstrated lifecycle scope and rely on Git/CI. One intermediate Codex
retry hit a client usage limit; retrying after the advertised reset succeeded without
purchasing credits, changing accounts or substituting a model.

Reproduction shape for Claude (use disposable fixtures, never personal data):

```sh
/path/to/fixture/scripts/dev session claude -p --setting-sources project \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --tools Read,Edit --allowedTools Read,Edit --no-session-persistence \
  --output-format stream-json --verbose '<fixture prompt>'
```

For Codex use `scripts/dev session codex exec --ephemeral --ignore-user-config
-s workspace-write --json`, adding one `-c hooks.<event>=<TOML array>` for each reviewed
SessionStart/PreToolUse/PostToolUse/Stop group and the invocation-local hook-trust flag
only for vetted disposable automation. Copy the tracked JSON groups to TOML inline
tables without changing command semantics; do not disable the tool sandbox. The
fixture instrumentation only wraps these commands to retain event/exit evidence.

Cloud orchestration and other AI clients were not tested as native lifecycle surfaces.
The source command, actual-index guard and required CI are their mandatory fallback.
No claim is made that trust, parsed JSON or a model's self-report proves hook delivery.

## CI, protection, issue coordination and cleanup

The workflow preserves both existing required Release checks context names, with
read-only permissions, and runs the actual generic release dry-run on Linux/macOS.
Linux passed the initial implementation. macOS was initially queued waiting for a
hosted runner. The PR Checks tab records results for each exact head revision; final
status and run links are included in the PR handoff rather than treating a queued
job as passed. The initial ARM job eventually failed before running any steps with
"The job was not acquired by Runner of type hosted even after multiple attempts";
annotations explicitly cited macOS ARM capacity. The workflow now maps the historical
macos-latest context to the standard `macos-15-intel` runner while retaining exactly
the same full gate and required context names. Local Apple Silicon checks also pass.
The supported Intel label was verified against the
[official runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Intel macOS then passed the full gate and archive dry-run. Linux correctly rejected
the new official runner label under the older actionlint 1.7.7 pin. Upgrading the
declared minimum and Linux pin to actionlint 1.7.12, with its declared Go 1.25
bootstrap requirement, keeps this validation active. Workflow YAML does not modify
server settings. Live protection was reread and remained strict/enforced.

#10's YAML defect is fixed and every agent/skill is now strictly parsed. #14's wider
skill authoring/semantic audit remains separate. #19's generic direct-packager cleanup
is not claimed complete; this toolkit extension stages only tracked explicit runtime
inputs. #20's cross-run gate reuse/merge-depth UX is unchanged; every invocation still
validates its exact commit. #18 marketplace dispatch is unchanged. #13 historical
root archive removal was not performed; new build output is explicitly outside source.
No related issue was closed or silently absorbed.

The disposable Claude, Codex and index worktrees and their three fixture branches
were removed after evidence collection; the initial archive worktree was also
removed. The feature worktree remains for review. Exact final-commit archive
verification uses another clean temporary linked checkout, removed before handoff.
Primary toolkit/Organon checkouts remain on their original clean main commits.
No managed hooks in unrelated repositories are modified.
