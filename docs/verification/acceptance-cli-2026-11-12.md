# CLI acceptance continuation — 2026-11-12

Issue: [toolkit #23](https://github.com/folotp/pa-toolkit/issues/23).
PA selected **Antigravity CLI only** for this acceptance continuation. App/IDE and
remote product modes are outside that selected target. Copilot remains exclusively
GitHub-hosted cloud-agent and PR-review scope; no local Copilot model was installed
or invoked. Claude's previously implemented CLI suite is historical passing evidence,
not certification of every interactive/Desktop/IDE surface.

## Source and evidence identity

Live main remained `31952d09694d14c4ddd0a1284e5d627f966d3b5c`; PRs #24 and #29
were verified merged and exact-main Linux/Apple Silicon CI remained successful:
[run 43279394305](https://github.com/folotp/pa-toolkit/actions/runs/43279394305).
Changes use the new `feat/toolkit-acceptance-cli` worktree. Existing worktrees,
branches, stashes and recovery snapshots were preserved.

[Sanitized receipts](acceptance-cli-2026-11-12.json) retain actual observer events,
source-tree/per-file hashes and client versions. The initial Codex/Antigravity runs
exported clean merged-main bytes (tree digest `84410d2f5e69e06276589b9d7e2c4da9e366f6b4ddcbb2db49e5fe048824bb7a`).
Later runner checks exported explicitly dirty feature-worktree bytes. Those receipts
identify each tested snapshot; they do not claim that every later documentation or
runner revision was executed by a model. The production launcher, adapters and shared
hook implementation remain unchanged from merged main. Observer instrumentation is
fixture-only; raw model transcripts, credentials and full user configuration are absent.

## Observed scenarios

| Surface / scenario | Result and actual proof |
| --- | --- |
| Codex CLI 0.167.2, independent project, user config ignored | BLOCKED for native hooks; fresh instructions and exact edit bytes pass, zero observer events |
| Codex ordinary configuration inspection | `hooks/list` selects primary-checkout definitions for linked root and subdirectory; all four project definitions enabled/trusted; no trust writes |
| Codex independent project configuration inspection | `config/read` reports project layer disabled until that exact project is trusted; `hooks/list` returns no project hooks |
| Codex linked root discovery and valid edit (A01/A02) | PASS: loaded marker, exact `ordinary.txt` bytes, start/edit/feedback/stop, all positive exits zero |
| Codex linked subdirectory multi-file edit (A01/A03/A04) | PASS: one actual `apply_patch` for both paths; shfmt diff, ShellCheck success and JSON parse diagnostic witnessed; deliberate bytes intact |
| Codex detached native denial (A05) | PASS: actual pre-edit observer exit 2 for `smoke.sh`; bytes unchanged |
| Codex main native denial (A05) | BLOCKED: main stays in the preserved primary checkout; no main edit attempted; an independent fixture would require project/hook review |
| Codex concurrent linked sessions (E01) | PASS: two separately selected fixtures overlap 53.039 s; each passes root/subdirectory edits, diagnostics and detached denial; per-client overall statuses remain BLOCKED for main |
| Antigravity CLI 1.5.7, root/subdirectory valid native edits (A01/A02/E01) | PASS twice: own loaded markers, exact bytes, actual `read_file`/`edit_file`, independent branches; first experiment overlaps 55.416 s, tracked runner 56.325 s |
| Antigravity deliberate multi-file defects (A03/A04) | Prior CLI smoke remains passing evidence; not repeated solely for a new session |
| Antigravity native hook scenarios | NOT APPLICABLE to the configured toolkit integration: no adapter is configured; Git/index/CI remains required |
| Copilot cloud agent | BLOCKED: explicit hosted task creation against `main` returned `403 Forbidden`; no task created; cause not established |
| Copilot PR review | BLOCKED on PR #30: review API returns 422 `ACTOR_INELIGIBLE`; legacy reviewer request returns success but no requested reviewer/submitted review was observed |
| Reduced docs/version PR CI (C02) | NOT RUN on a genuine hosted docs/version PR; conservative full behavior and full main/release validation retained |

## Why the previous Codex blocker was ambiguous

The independent runner's `--ignore-user-config` mode deliberately omits existing
project trust. A fresh repository consequently has no active project hook layer.
The read-only installed app-server inspection establishes that configuration state;
zero hook records alone could not distinguish it from a delivery failure.

With ordinary existing configuration, Codex 0.167.2 selects the primary checkout's
`.codex/hooks.json` for these linked worktrees. Those exact definitions were already
trusted. Their commands resolve the invoking Git root, so the fixture's unchanged
hook function and observer receive real native events. No trust/permission setting,
hook definition, sandbox mode or client installation was changed to obtain the proof.
This establishes this installed version and configuration, not every Codex surface.

The runner now offers `--codex-fixture` for an explicitly selected, clean linked
`chore/acceptance-codex-*` branch at the selected source HEAD. It refuses ordinary
branches, dirty/staged/untracked work, another repository, source deletions that an
overlay would leave stale, and changed source bindings that could be confused with
older primary definitions. It exports source bytes, preserves the fixture/index,
and restores its original branch on exit, including timeout. It never switches
primary main or force-reuses another checkout. Main denial remains BLOCKED and exit
status remains nonzero. Independent ignored-config mode remains available and honest.

The current task itself initially rejected a native patch addressed outside its main
startup cwd. No source edit occurred. Source changes were subsequently preflighted
through the unchanged canonical guard from the actual feature cwd, then applied
there, with Git/index/CI checks enabled. These manual source-edit guard calls are
separate from the native model-backed event evidence above.

## Reproduce and inspect

Use the [maintained plan](../agent-test-plan.md) and [development runbook](../development.md).
Create a new disposable linked fixture; preserved dirty fixtures are not reused:

```sh
./scripts/dev worktree chore/acceptance-codex-example /outside/source/codex-fixture
python3 scripts/verify-agent.py --client codex --codex-fixture /outside/source/codex-fixture --output /outside/source/codex.json
python3 scripts/verify-agent-concurrency.py --output /outside/source/antigravity-concurrent.json
```

The Codex linked command intentionally returns nonzero for the outstanding main
scenario. Inspect its individual outcomes rather than promoting a partial run to PASS.
For concurrent Codex proof, create two new fixtures and start one linked command per
fixture concurrently with distinct output paths. Record overlapping start/end times
and retain each full receipt; compare each checkout's events, branches and exact bytes.
The Antigravity concurrency command creates/removes only its own independent temporary
repository and linked worktree; source and pre-existing checkouts remain untouched.

Read-only installed-protocol inspection used `codex app-server --enable hooks`:
initialize with `experimentalApi: true`, then request `hooks/list` with explicit
`cwds`, and `config/read` with `cwd` and `includeLayers: true`. Keep only project
hook metadata and layer names/disabled reasons, never full user configuration. This
is discovery evidence, not native-delivery evidence. The protocol schema was generated
from installed 0.167.2; recheck it for another version. No thread/model turn is needed.

The bounded Copilot cloud prompt requests only a useful evidence document, discovered
instructions and doctor/full-check results, on its own hosted branch/PR based on main.
`gh agent-task create --repo folotp/pa-toolkit --base main --from-file <prompt>` returned
403. The GitHub connector has no task-creation capability; GitHub UI access was also
unavailable in this session. Neither failure proves that PA lacks a subscription or
that the repository disabled Copilot. An authorized hosted surface/access remedy is
needed; paid-service activation and broader permissions were not attempted.

The dedicated review request on [PR #30](https://github.com/folotp/pa-toolkit/pull/30)
returned HTTP 422 `ACTOR_INELIGIBLE`, identifying either a license without code review
or an organization Copilot policy. Those alternatives were not distinguished. A legacy
reviewer request through the connector returned success; a subsequent REST read showed
no requested reviewer and no submitted review. A successful request is not a model
review. The receipt retains the request head and observation time. No service, billing
or permission setting was changed. Check the PR for any later actual review.

## Current official sources and remaining boundaries

The receipts contain retrieval timestamps, URLs and SHA-256 digests for current
[Codex hooks](https://learn.chatgpt.com/docs/hooks),
[Copilot hosted tasks](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-from-cli),
[Copilot review API](https://docs.github.com/en/rest/pulls/copilot-code-review),
[Antigravity CLI guidance](https://antigravity.google/docs/cli/best-practices/) and
[Antigravity hooks](https://antigravity.google/docs/hooks/).
These prose contracts require semantic review; fetching them is not machine certification.
Antigravity documents its own hook schema and camelCase payloads. Absence of a toolkit
adapter is not a claim that Antigravity lacks hooks. Native adapter implementation is
outside this configured Git/index/CI integration and must not copy Claude bindings.

Automated Codex PR review found that the initial deletion preflight omitted staged
removals/renames. The guard now compares HEAD against the complete source state with
rename detection disabled, rejecting old paths that a linked overlay would retain.
Two dedicated regressions preserve fixture bytes for staged removal and staged rename.
This review is Codex evidence, not the outstanding Copilot acceptance requirement.
The next review also found that a later blocked main scenario overwrote an observed
detached guard failure. The aggregate now preserves FAIL; a probe-level regression
simulates changed forbidden bytes after passing positive scenarios and asserts FAIL.

The required current-official-spec gate, conservative PR selection and full
main/release validation are preserved. Full source/index gates and installed pre-commit/pre-push passed with 83 tests;
[current-head CI belongs to PR #30](https://github.com/folotp/pa-toolkit/pull/30). No merge, release/tag, marketplace action, trust change,
vault write, CodeQL implementation, other-repository rollout or deployment occurred.
Issue #23 stays open for the outstanding applicable requirements, including hosted
Copilot access/review, main native proof and any separately requested instruction-mirror
recheck. No vault mirror was read or changed in this scoped continuation.
