# Development acceptance and evidence

[Issue #23](https://github.com/folotp/pa-toolkit/issues/23) completed the shared
development-tooling implementation. PA accepted the recorded coverage and closed
the issue. Untested or access-blocked scenarios remain explicit limitations;
acceptance does not mean every product surface passed a native test.

## Completion baseline

PRs #24 and #29–#34 merged the shared interface, official specification checks,
conservative CI, native adapters, reusable probes and operational documentation.
The completion baseline is `abdc390bb39d0b19cd09640556713fb2b0c48899`.
[Exact-main CI](https://github.com/folotp/pa-toolkit/actions/runs/43364424028)
ran the full gate on Linux and Apple Silicon: 109 deterministic tests per platform,
current official-spec validation and real archive validation. The macOS job
confirmed ARM64/arm64. These are baseline results, not attestations for later code.

The required checks remain `Release checks (ubuntu-latest)` and
`Release checks (macos-latest)`. At closure, main protection required both checks
with strict status checking and admin enforcement, prohibited force pushes/deletion,
and required the PR route with zero required review approvals. Future changes must
verify their own current-head results and preserve the repository's protection policy.

## Recorded native coverage

| Surface | Recorded evidence | Limits |
| --- | --- | --- |
| Codex local CLI 0.167.2 | Trusted linked root/subdirectory discovery, native edits, full shell/JSON diagnostics, unchanged defect bytes, detached denial and production invocation receipts; linked concurrency recorded | Independent ignored-config/main-native proof remains blocked by project/hook review; desktop behavior is unproven |
| Claude Code local CLI 2.1.323 | Root/subdirectory discovery, three sequential native edits per linked checkout, diagnostics, start/pre/post/Stop response and production receipt correlation; separate main/detached denial | Local CLI results do not certify cloud/interactive products; the separate branch probe used a labelled fixture observer |
| Antigravity CLI 1.5.7 | Native instruction discovery, text/multiple-file edits and overlapping linked-worktree execution | No native hook adapter; App/IDE outside the selected CLI target |
| Claude Code cloud via desktop/web | User-run comments report loaded root instructions, native Edit/Write diagnostics, unchanged fixture hashes and readiness; an earlier run reported detached/path-escape denial | Comment-backed evidence; raw cloud artifacts not retrieved. Marker/main/Stop/receipt/concurrency scenarios incomplete; latest run had absent Git hooks, unset tracing and conflicting binary/environment version claims |
| GitHub Copilot hosted agent/review | Repository discovery guidance and required CI are implemented | Native hosted acceptance access-blocked (403 task creation / 422 ACTOR_INELIGIBLE); no Copilot-model pass claimed |

The latest local Claude linked run tested clean production source `0e1d9be` and
recorded 15.906 seconds of overlapping client-process windows, including tool time.
That is not a model-inference scheduling measurement. Codex's fresh receipt run
correlated 11 production records with observed event/tool/exit tuples. Source and
harness hashes identify the recorded implementations; later changes need their own
relevant validation.

The returned Codex desktop attempt ran on a cloud executor without access to the
Mac fixture. It established an execution-host mismatch, not a desktop product defect.
The cloud client-version conflict (binary 2.1.323 versus environment 2.1.42) remains
unresolved. Expected hash consistency is not retrieval of the actual cloud files.

## Durable evidence and future checks

Issue #23 contains the acceptance decision, result comments and source/PR/CI links.
Detailed historical reports and sanitized recordings remain available in
[the completion tree's verification directory](https://github.com/folotp/pa-toolkit/tree/abdc390bb39d0b19cd09640556713fb2b0c48899/docs/verification).
They were removed from the current tree after closure along with session prompts
and handoffs. Git history preserves provenance without making run-specific data
part of the maintained documentation.

Use the [reusable acceptance plan](agent-test-plan.md) for future changes. Native
model calls remain optional acceptance work, separate from deterministic CI. Keep
PASS/FAIL/BLOCKED/NOT RUN/NOT APPLICABLE honest; project trust, configuration parsing,
model narration and manual hook calls do not prove native delivery. The remaining
surface-specific cases are non-blocking follow-up coverage accepted at issue closure.

The [architecture](development-architecture.md), [runbook](development.md),
[hook scope](hook-scope.md) and [SDK contract](shared-devtools.md) are the maintained
operational sources. The SDK's initial wheel/resource/interpreter checks are recorded
in the historical reports; consumers must verify their own pinned installation and
distribution before adoption. Cross-repository rollout and releases remain separate work.
