# Linked-worktree acceptance after PR #32

## Merged baseline

PR #32 merged as `0e1d9be81f05beb1d0d2f5b1f619eead1a73f567`; its remote
feature branch is absent. The clean primary checkout was fast-forwarded to that
commit, preserving all existing worktrees/branches/fixtures. Exact-main
[CI 43356364430](https://github.com/folotp/pa-toolkit/actions/runs/43356364430)
passes both required Linux/Apple Silicon jobs. This is post-merge validation,
separate from the previous PR-head checks.

The new implementation branch is `feat/claude-linked-acceptance`. No release,
tag, marketplace update, global trust change or old-fixture cleanup is part of
this continuation. The prior [cloud/desktop result review](native-results-followup-2026-11-12.md)
remains the authority for those user-run reports and their artifact limits.

## Actual Claude Code linked-worktree test

Claude Code **2.1.323**, local CLI print, tested clean merged source `0e1d9be`.
The exported source-tree SHA-256 is
`808e56f209d39c812c2f7a0135961a4ae74182951c7e48ee1a1ef77a400e7e5a`.
The [sanitized evidence](linked-acceptance-2026-11-12.json) retains the source
file hashes, runner digest, structured native calls/responses, production invocation
receipts, resulting fixture hashes, checkout changes and process overlap.

The extended runner exports clean source into a new temporary repository, creates
a second linked worktree, and gives each checkout its own random instruction marker.
One client launches at root; the other invokes the shared launcher from `scripts/`,
which normalizes that child's cwd to its own checkout root. Both run concurrently
with only Read/Edit tools and an empty strict MCP configuration. Project settings
remain enabled; no permission, hook-review or sandbox bypass is used. These tests
exercise local CLI behavior, not Claude cloud or an interactive trust prompt.

| Scenario | Observed result |
| --- | --- |
| A01 | PASS: both returned their distinct already-loaded markers, without native reads of instruction files |
| A02 | PASS: native Edit produced each checkout's distinct expected ordinary.txt bytes |
| A03 | PASS: native PostToolUse shell shfmt diff and JSON parser error, exact intentional defect bytes preserved |
| A04 | PASS for three sequential Edit calls per checkout; no MultiEdit claim |
| Lifecycle | PASS: each stream contains successful SessionStart, three PreToolUse, three PostToolUse and Stop responses, correlated with eight production receipts |
| E01 | PASS: 15.906 seconds of overlapping actual client-process windows in different linked worktrees; branches, HEADs and changed paths match expectations |
| Source isolation | PASS: source HEAD, status and all exported source-file hashes unchanged |

Production `scripts/dev.py` and bindings are copied unchanged. The new trace mode
records invocation metadata in separate private external files, without injecting
an observer into either checkout. Native structured responses provide diagnostics
that the minimal trace deliberately omits. A receipt alone is insufficient; passing
requires native Edit path coverage, successful response/receipt exits and outcomes,
both diagnostics and exact bytes. Model prose cannot substitute for hook responses. Single-client and concurrency
adapters share `diagnostic_coverage`: require the expected removed/added shell
lines, ShellCheck success and the exact JSON diagnostic on the corresponding path.
Header-only formatter output fails in both unit and end-to-end controls.

The recorded overlap measures child process execution, including tool time. It is
not a claim about simultaneous model inference. The runner removes only its own
temporary repository/worktree after recording; all pre-existing fixtures are preserved.
Earlier runs passed with 17.339, 16.318, 16.451 and 15.260 seconds of overlap. The tracked
after-review run uses per-invocation tool/response/receipt correlation and records
15.906 seconds; its runner digest identifies the corrected harness.

## Fresh Claude native branch denials

A separate run of `verify-agent.py --client claude` tested the same clean merged
source/version. Its implemented root/subdirectory edit and diagnostic scenarios
pass, along with actual native **main and detached-HEAD denial**. This run uses
the existing explicitly fixture-only observer to retain bounded hook output;
it is independent of the unmodified production receipt demonstration above.
The disposable repository was removed, source commit stayed unchanged, and no
primary branch was switched. These results do not certify cloud branch denial.

## Fresh Codex production receipt delivery

Codex CLI 0.167.2 ordinary trusted linked mode tested the same clean merged source.
Root/subdirectory discovery, actual apply_patch edits, both diagnostics, non-mutated
fixture bytes and detached denial PASS. A newly named explicitly disposable fixture
is preserved at acceptance-codex-receipts-20261112, on its original chore branch,
with intentional probe changes. None of the older fixtures was reused or removed.

All **11 production invocation records** match the fixture observer's event/tool/exit
sequence: root start/edit/feedback/stop; subdirectory start/edit/feedback/stop; detached
start/rejected-edit/stop. The rejection has exit 2; positive events have exit 0. This
pairs minimal production metadata with observed native hook output; it is not a
receipt-only claim. The probe retains ordinary configuration/trust and workspace-write
sandboxing, with no bypass or new trust grant.

Aggregate status is **BLOCKED**: native main denial cannot be tested by switching the
preserved primary main into this linked fixture. The independent main root still
requires supported project/hook review. Desktop behavior and the independently
ignored-config route are not certified by this ordinary trusted CLI run.

## Runner controls and scope

`verify-agent-concurrency.py --client claude` adds Claude to the existing runner;
Antigravity remains its default with the prior native edit-only contract and no
native-hook claim. Shared setup, checkout inspection, process execution/timeout,
provenance and aggregate status remain common to both clients. No dependency added.

Deterministic fake-client controls are separately labelled: a complete synthetic
run passes; missing receipts block; failed native-response exits or missing
expected diagnostics fail. Unit controls reject explicit instruction-file reads,
exclude model prose from diagnostics, require native Stop coverage, redact resolved
macOS roots, and prove that timeout cannot conceal a changed HEAD or extra path.
The existing Antigravity untracked-path regression still passes. These controls
validate the harness; they are not additional real-client acceptance evidence.

PR #33 review hardening requires exactly one native Edit per target, and correlates
each invocation with the ordered pre/post native responses (including their Edit
hook-name binding) and production receipt event/tool sequence. A fourth Edit,
Write-labelled receipt, swapped pre/post sequence or extra receipt cannot pass.
Missing telemetry remains BLOCKED. Unit and end-to-end fake-client regressions
cover the review's two reproductions. An independent byte-integrity check also
rejects corrupted/deleted fixtures even when the client fails, while unfinished
fixtures still at their original bytes remain unproven rather than corrupt.

The subsequent timeout/error review fixes retain partial stdout/stderr through the
shared process-group termination/drain helper and parse those observations before
classifying the run. A flushed native Read of AGENTS.md followed by a timeout is
FAIL; a clean timeout or authentication error with only the runner's marker change
is BLOCKED. Missing intended edits are exempted for any incomplete client run,
while extra paths, changed HEADs and invalid bytes remain failures. Deterministic
controls exercise these cases, plus text/byte timeout compatibility, actual SIGTERM
drain output and the forced-SIGKILL drain path. Raw streams remain transient; only
sanitized native observations are retained.

The positive native refresh above has no timeout. Timeout/error behavior is
separate deterministic evidence. The harness consistently loads its own shared validator/process helper, including
when `--source` selects an older production snapshot. `harness_hashes` records both
executed harness files; source hashes identify exported production independently.
Python byte/text timeout output is normalized without discarding observations.

The source digest above identifies clean **production source**; `runner_sha256`
and `harness_hashes` identify the feature runner and its shared helper separately. Documentation/tests added after a live
run do not retroactively become tested production bytes. Current PR-head full/index
and hosted Linux/Apple Silicon gates are still required for the implementation.

## Remaining selected-surface boundaries

Issue #23 remains open. Local Claude linked-worktree concurrency is now observed,
and local production receipts have native delivery proof. Claude cloud still needs
fresh marker/entry-point discovery, main-native denial, toolkit Stop and cloud
concurrency evidence. Codex desktop remains blocked by the returned cloud-host
mismatch; its independent main-native prerequisite remains separate. Copilot hosted
task/review remains access-BLOCKED without changed entitlement evidence. No unchanged
access request, denied UI route, paid activation or CLI-for-cloud substitution was used.


## Implementation validation

Locked sync, doctor and the full shared gate pass in the new feature worktree,
including 109 deterministic tests, current official-spec validation, source checks,
links, inventory and package contract. The actual-index gate and normal Git hooks
must pass before the implementation commit; final-head Linux/Apple Silicon CI
and configured review remain required. Those checks validate the feature harness,
while the native recordings above identify the clean merged production snapshot
separately. No additional production hook policy or runtime package file was added.
