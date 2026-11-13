# Native results continuation for issue #23

## Provenance and baseline

This continuation reads the [full handoff](https://github.com/folotp/pa-toolkit/issues/23#issuecomment-6835923390),
[review addendum](https://github.com/folotp/pa-toolkit/issues/23#issuecomment-6837256514),
[consolidated Claude cloud report](https://github.com/folotp/pa-toolkit/issues/23#issuecomment-6837791220)
and [Codex desktop attempt](https://github.com/folotp/pa-toolkit/issues/23#issuecomment-6841843740).
The consolidated Claude report supersedes earlier comments by that run, including
the addendum's statement that no Git commit/push behavior was exercised: disposable
clones exercised it later; the task checkout itself never committed/pushed.

Local HEAD and fetched origin/main were both `1e0a7f63b8e9159006d3814630e874eb1f83d278`
on resumption. The primary checkout was clean. PR #31's
[exact-main full CI](https://github.com/folotp/pa-toolkit/actions/runs/43305468641)
is the handoff's merged baseline, not evidence for this follow-up's changed source.
The handoff also records actual reduced docs-only PR #31 run
[43301783154](https://github.com/folotp/pa-toolkit/actions/runs/43301783154), so C02
is historically observed, not awaiting its first observation.

The [original comment snapshots](native-results-comments-2026-11-12.json) are durable
agent-authored self-reports with selected native witnesses. Raw cloud files/event
streams and Codex fallback artifacts were not retrieved. Independently recomputed
[expected bytes/hashes](native-results-expected-bytes-2026-11-12.json) match the cloud
report's abbreviated endpoints; this verifies hash consistency only. It does not
verify the contents of the ephemeral container. Existing production hook contracts
match the reported diagnostic/denial wording. Historical receipts certify their
recorded source/product/scenarios only; changed hook code needs new native evidence.

## Claude Code cloud: reported observations

Run `cc-cloud-20261112T2110Z`, 2026-11-12 21:08–22:25 UTC. Claude Code 2.1.322,
configured model claude-sonnet-5-5, Linux x86_64, remote_desktop entry point,
CLAUDE_CODE_REMOTE=true. Branch `claude/epic-hypatia-18h9sy`; reported clean before
and after at exact 1e0a7f6. No subordinate model/CLI substituted for the session.

| Scenario | Status and evidence boundary |
| --- | --- |
| A01 | PARTIAL: CLAUDE.md import/AGENTS and SessionStart loaded at root; random marker and fresh subdirectory session NOT RUN. Later file reads are not automatic discovery |
| A02 | Reported PASS: native Edit, exact after bytes, advisory structural-acceptance context |
| A03 | Reported PASS: native Write shell shfmt diff and JSON parser error, unchanged deliberate defects |
| A04 | Reported PASS for sequential Edit/Write/Write with per-path feedback; MultiEdit unavailable, not inferred |
| A05 | Reported PASS detached Edit and Write denial, outside-root and symlink escape denial; main-native NOT RUN |
| Shell writes | Observed unguarded on detached HEAD; existing documented native matcher limit; Git/index and CI remain required |
| Stop | NOT WITNESSED; manual call and subsequent absence of advice are not native proof |
| G01/G02/G03 | Reported PASS in disposable clones with local bare remote; separate from native model evidence and from the task checkout's installed hooks |
| E01 | NOT RUN for cloud concurrency |
| E02 | Reported missing/old actionlint failure with remedies; task-local v1.7.12 resolved that container |
| S01/S03 | Reported current official source validation; prose semantics MANUAL_REVIEW |
| S02 | Reported dead-proxy failure; upstream-new-field half NOT RUN in cloud. Existing deterministic new-required-field regression remains separate |
| P01 | Reported clean local archive PASS, 30 entries, no publication; archive was not retrieved |
| C01–C03 | Not exercised by this cloud task; baseline hosted CI evidence remains separately scoped |

Raw hook payloads/exits and PreToolUse allow events were not exposed. Environment
hooks repeatedly asked to commit defect fixtures; the task declined and later
removed fixtures only after PA's authorization and external byte-identical copies.
This was not repository Stop delivery. Ephemeral root execution/proxy connectivity
does not establish secrets, egress or branch-protection isolation.

## Codex desktop: execution-host mismatch

The returned attempt observed 2026-11-13 02:15:43 UTC ran in a managed Linux cloud
executor at /workspace. No app terminal was attached. The Mac worktree/recovery
paths were inaccessible, the loaded marker absent, desktop version/model unavailable,
and no target hashes, edits, hooks, diagnostics or denial were observed. Status
remains BLOCKED, not a desktop product failure or a passed desktop scenario.

On this Mac, the rendezvous report directory and native-events file were still
absent on resumption. The existing Mac desktop fixture and all other registered
fixtures are preserved. Do not copy later instruction reads into discovery proof.
Next native attempt must first establish local Mac execution with access to the
prepared fixture, without spawning a CLI substitute or changing global trust.
No denied UI automation was retried. Copilot access/entitlement remains BLOCKED;
no unchanged task/review retries or paid activation were performed.

## Implemented response to the cloud recommendations

| Recommendation | Disposition |
| --- | --- |
| Cloud prerequisites and missing Git layer | Added reviewed per-clone setup route and pinned actionlint guidance; no hosted environment settings changed or future persistence claimed |
| Stop visibility and conflicting environment hooks | Added opt-in minimal invocation receipts and conflict-handling guidance; cloud Stop remains unproven |
| Matcher/tool drift | Regression binds current Claude matchers to supported payloads; NotebookEdit/new tools explicitly outside scope. No speculative adapter expansion |
| One session per worktree; advisory feedback | Documented session-root resolution and post-edit context versus mandatory Git/CI enforcement |
| Harness branch prefixes | Actual staged-check and destination-guard regression for claude/cloud-acceptance; creation helper keeps documented prefixes |
| Personal connector skills | Cloud acceptance restricted to development tooling |
| Installer scope, directory and permission errors | Prints Git-resolved destinations/shared scope, preserves external hooksPath behavior, gives actionable errors; later I/O failures may be partial |
| Root-sensitive permission tests | Inject real PermissionError type rather than rely on ineffective root mode-bit tests; cloud's non-root experiment remains a separate reported observation |
| Common enforcement and additional branch cases | Git/index plus required CI are shared gates. main is the protected destination contract; no master/release policy invented. Force does not change pre-push destination fields |
| Fresh discovery/native delivery | Still needs actual selected entry points. CLI random-marker runner already exists; new receipt mode supports future cloud session evidence without claiming a cross-surface launcher |
| Network/secrets/trust limits | Explicit observed versus untested boundaries; no configuration parse treated as delivery |

These source changes are deterministic test coverage and preparation for native
reruns. They do not retroactively certify desktop/cloud receipt delivery. The
active resumption session's native patch rejected a path in the feature worktree
because its own root was the primary checkout; no file changed in that call.
Implementation uses the documented shell-edit path in the named feature worktree,
with actual-index/Git/CI checks, and makes no native-hook claim for those edits.

## Remaining work

Issue #23 stays open. Required follow-ups: local Codex desktop native acceptance;
independent Codex main-native denial through supported reviewed hooks; fresh Claude
cloud marker/subdirectory discovery, main-native denial, Stop witness and cloud
concurrency; Claude linked-worktree concurrency; and Copilot hosted task/review when
access changes. Interactive entry-point prerequisites remain as previously recorded.
MultiEdit can be tested if exposed, rather than substituted with an unsupported
name. No personal MCP, global trust change, fixture cleanup, merge or release is
needed to claim this bounded continuation complete.


## Follow-up validation

Locked sync and doctor pass in the new feat/native-acceptance-followup worktree.
The full shared gate passes 98 deterministic tests, current official specification
resolution/validation, source checks, links, inventory and runtime package contract.
The new tests cover receipt concurrency and unsafe destinations, real CLI advisory/
rejection exit receipts (including malformed tool names), unchanged native-guard
semantics (including symlink-loop and held-lock receipt failures), installer directory/permission remedies, Claude matcher agreement and
cloud-branch staged/push behavior. No dependency was added. The permission error is
injected, so root cannot accidentally defeat a mode-bit assertion.

The actual-index gate and normal Git hooks must pass before committing this source;
hosted Linux/Apple Silicon CI must pass for the final PR head. These source changes
have no new native desktop/cloud acceptance receipt yet. CI run/PR identities belong
to the live PR, not the earlier 1e0a7f6 baseline above.
