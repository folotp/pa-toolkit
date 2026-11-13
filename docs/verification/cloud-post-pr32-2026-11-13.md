# Claude Cloud result review after PR #32

## Source and verification limits

The [new cloud report](https://github.com/folotp/pa-toolkit/issues/23#issuecomment-6842713672)
is headed PA-ACCEPTANCE / CLAUDE-CLOUD / POST-PR32. Its session started
2026-11-13 03:13:52 UTC in an ephemeral Linux x86_64 cloud_default container,
CLAUDE_CODE_REMOTE=true, through remote_desktop. The reported task branch was
claude/stoic-brown-l3i2f9 at `0e1d9be81f05beb1d0d2f5b1f619eead1a73f567`,
matching origin/main at that time. PR #33 merged later, at 03:54:54 UTC, as
`c8f2b58d7a78b1994f430e183bdd11353bc34d4a`; this is not a cloud test at c8f2b58.

The [durable comment snapshot and independent checks](cloud-post-pr32-2026-11-13.json)
retain the original report, recomputed expected-byte hashes and production-file
comparisons. Raw cloud fixture copies, hook payloads/exits and process streams were
not retrieved. Results remain agent-authored comments with selected native witnesses.
Matching expected hashes verifies internal consistency, not retrieval of actual files.

`claude --version` reportedly returned **2.1.323**, while CLAUDE_CODE_VERSION was
**2.1.42**. The binary and environment claims conflict; the running session's exact
client version remains unresolved. The configured model was taken from the session
prompt, not independently verified. No upgrade or environment correction was made.

## Reported observations

| Scenario | Result and boundary |
| --- | --- |
| Root instruction loading | PARTIAL discovery: CLAUDE.md plus imported AGENTS.md reportedly arrived before explicit reads; SessionStart context was visible |
| Random-marker discovery | NOT RUN: no pre-start marker challenge established. A marker must be planted before startup and must **not** appear in the task prompt |
| Readiness | Reported PASS: locked sync and doctor exit 0, actionlint 1.7.12 present in this fresh run; full `scripts/dev check` was not reported |
| Git layer | ABSENT in this checkout: pre-commit/pre-push reported missing/legacy/unmanaged and were deliberately not installed |
| A02 | Reported PASS: native Edit ordinary.txt produced after plus final newline |
| A03 | Reported PASS: native Write shell delivered formatter diff and ShellCheck success; native Write JSON delivered exact parser error; defects remained intact |
| A04 | Reported PASS for three sequential paths; MultiEdit not exposed |
| Native main denial | BLOCKED before any attempt: local main was 1e0a7f6, an ancestor of task HEAD 0e1d9be; no branch movement/edit occurred |
| Stop / receipts | NOT OBSERVED: tracing unset in the client environment, no toolkit Stop output or receipts; not a trace implementation failure |
| Cloud concurrency | NOT RUN |

There was no exposed PreToolUse allow output, raw payload or hook exit code.
All three reported final hashes match independently recomputed expected bytes.
The reporter retained originals in an untracked fixture directory and a reportedly
byte-identical task-private external copy. Only that untracked directory was listed
in Git status; task branch/HEAD were reported unchanged, with no commit or push.
No cloud fixture cleanup or mutation was performed from this Mac continuation.

Actionlint availability is progress over the initial cloud run, but one reported
fresh environment does not prove the stored environment definition or every future
session. Doctor readiness does not establish installed Git enforcement. The earlier
[cloud report](native-results-followup-2026-11-12.md) retains its own baseline and
reported detached/path-escape denials; those scenarios were not rerun here.

## Compatibility with merged PR #33

Current primary main was fast-forwarded cleanly to c8f2b58 after verifying the merge
and remote feature-branch deletion. [Exact-main CI](https://github.com/folotp/pa-toolkit/actions/runs/43362071694)
passes Linux and Apple Silicon. Existing worktrees, branches and intentional
fixtures were preserved; this continuation uses a new docs worktree.

Tracked bytes are identical between reported 0e1d9be and merged c8f2b58 for the
launcher, development hook implementation, shared hook helpers, Claude/Codex
bindings and branch guard. This supports compatibility of the reported hook behavior
with the merged implementation. It does not certify a fresh native cloud run at
c8f2b58, resolve client identity or turn missing telemetry into a pass. PR #33's
local CLI concurrency/receipt evidence remains separate from cloud.

## Focused continuation

The [copyable follow-up](claude-cloud-followup.md) separates a bounded main-denial
continuation in the existing task-owned cloud clone from marker/Stop tests that
need preparation before a fresh client starts. It explicitly allows only a safe
local-main fast-forward to the captured task HEAD under stated conditions; no force
update, remote change or switch of the Mac's main is involved.

An export in a tool's child shell cannot configure its already running parent
client. If no supported cloud startup environment route is available, record that
as the receipt/Stop prerequisite rather than claiming tracing was enabled. The
marker must also exist before instruction loading; adding it after an explicit
read cannot repair discovery evidence retroactively.

Issue #23 stays open. Remaining: cloud marker/entry-point discovery, native main
denial, Stop/receipt delivery and cloud concurrency; actual Codex desktop access and
independent main-native review; Copilot hosted access/entitlement. No unchanged
Copilot request or denied UI route was retried. No production enforcement change
is justified by this report's unconfigured or unattempted scenarios.


## Documentation validation

Locked sync, doctor and the full shared gate pass in docs/claude-cloud-post-pr32,
including 109 deterministic tests, current official-spec validation, source checks,
links, inventory and package contract. No production code/dependency/runtime
inventory changed. The normal actual-index Git gate must pass before committing;
this documentation PR needs its own hosted checks and configured review. Those
checks validate repository changes, not a new Claude Cloud native execution.
