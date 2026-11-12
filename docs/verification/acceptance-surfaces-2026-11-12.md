# Post-merge checkpoint and surface acceptance

## Verified baseline

On 2026-11-12 local and remote main remained at
`5b5fe08cdc77d59d83d791985df27cd5a0bd2144`, clean, with a tree identical to
PR #30 final head `9ef92808b4d8c92dc99a60a2b51fc53a79ae3e65`.
PR #30 is merged and its remote feature branch is absent. No pull/reset was needed.
[Exact-main CI](https://github.com/folotp/pa-toolkit/actions/runs/43298112159)
passed both required Linux/Apple Silicon contexts: 86 tests per platform,
required live official specifications and a real 30-entry archive. This is full
main evidence, not C02 reduced docs-only PR proof. Issue #23 remains open.
All existing worktrees, dirty fixtures, branches and recovery directories are preserved.

## Product and scenario matrix

The statuses below describe native model evidence, unless explicitly labelled
unit/CI. Historical CLI recordings are in the
[previous report](acceptance-cli-2026-11-12.md); source hashes constrain their reuse.
CLI-only selection applies exclusively to Antigravity. Product selection for the
other available surfaces is pending PA's usage clarification, not excluded by default.

| Client / surface | A01 discovery; A02 valid edit | A03 diagnostics; A04 multi-file | A05 native denial | E01 independence; E02 prerequisites | Remaining boundary |
| --- | --- | --- | --- | --- | --- |
| Codex CLI exec, ordinary configuration | Fresh merged-source PASS root/subdirectory | Fresh merged-source PASS with exact bytes/events | Fresh detached PASS; main BLOCKED | Linked concurrency PASS historically; independent trust BLOCKED | Interactive terminal is a separate entry point |
| Codex interactive terminal | NOT RUN | NOT RUN | NOT RUN | NOT RUN | `/hooks` review route exists; no blanket trust changes authorized |
| Codex desktop/local computer session | NOT RUN | NOT RUN | NOT RUN | NOT RUN | Current task uses local computer tools, but that is not a controlled fixture acceptance recording |
| Codex IDE / hosted | NOT RUN, selection pending | NOT RUN | NOT RUN; check adapter applicability | NOT RUN | Do not extrapolate local hooks into hosted orchestration |
| Claude Code CLI print | Fresh merged-source PASS root/subdirectory | Fresh PASS; two native sequential edits | Fresh main and detached PASS | Independent concurrent runs PASS; linked concurrency NOT RUN; prerequisite fixtures unit-tested | Shell/MCP native edit coverage unproven |
| Claude Code interactive terminal | BLOCKED at folder trust prompt | NOT RUN | NOT RUN | Explicit native prerequisite observed | Selected “No, exit”; no trust settings changed |
| Claude Code desktop / IDE / web | NOT RUN, selection pending | NOT RUN | NOT RUN; check adapter applicability | NOT RUN | Claude.app and VS Code installed; installation alone proves no integration/authentication |
| Antigravity CLI | Recorded PASS | Recorded smoke PASS | N/A, no adapter | Recorded overlapping linked edits PASS | App/IDE excluded by explicit selection |
| Copilot hosted cloud agent | BLOCKED | BLOCKED | N/A local hook parity | Task create 403 on renewed attempt | No actual task created; no service activation authorized |
| Copilot GitHub PR review | Separate reviewer scenario | Separate reviewer scenario | N/A local hook parity | Fresh PR #31 422 ACTOR_INELIGIBLE | No actual submitted Copilot review; entitlement/policy alternatives unresolved |

G01–G03 and E02 failure controls are deterministic fixture coverage, not native
model proof. S01–S03 require live-source receipts plus manual semantic review limits.
P01/C01/C03 have merged-main hosted evidence above. C02 awaits observation of this
genuine scope/status documentation PR; full fallback remains correct if required
baseline proof is unavailable. No policy/routing relaxation is part of this change.

## Priority access boundaries

A new independent disposable `main` repository was prepared outside the source at
`/Users/pierreandre/Developer/Recovery/pa-toolkit-surfaces-2026-11-12/codex-main-fixture`.
Its review receipt identifies all exported source hashes, unchanged `.codex/hooks.json`
and sole prospective edit target `ordinary.txt`. It has no observer modifications,
installed Git hooks, trust changes or bypass options. This prepares a reviewable
fixture; it is not native denial proof. Native proof needs actual delivery plus
unchanged target bytes and an explicit hook denial, not just model refusal.

[Official Codex hook documentation](https://learn.chatgpt.com/docs/hooks) requires
trusted project configuration and exact hook-definition review. The supported CLI
route is `/hooks`; desktop offers hook review through its settings/composer.
The current no-global-trust-change boundary remains in force. No project trust or
hook trust was copied, enabled or bypassed to turn BLOCKED into PASS.

The renewed bounded hosted task attempt using `gh agent-task create`, explicitly
based on main and the previously reviewed documentation-only prompt, still returns
`403 Forbidden`. Read-only repository metadata confirms owner type `User` and admin
repository permissions. Thus organization-policy diagnosis cannot be assumed for
this personal repository; the exact entitlement/account prerequisite remains unknown.
Task-list access returns an idle entry without repository/PR identity; it is not
proof of a newly executed task.
[GitHub's review documentation](https://docs.github.com/en/copilot/concepts/agents/code-review)
distinguishes paid-plan entitlement and policy restrictions. An account settings
inspection by PA is needed if API access cannot distinguish them. Do not activate
paid usage, broaden credentials or change policies as an acceptance workaround.

## Evidence handling and follow-up

External receipts live under
`/Users/pierreandre/Developer/Recovery/pa-toolkit-surfaces-2026-11-12`.
Only sanitized results should be committed. Source hashes, observer changes and
actual model events remain distinct from deterministic stubs/replays. This report
must not close #23 while applicable native/product scenarios remain unresolved.

## Fresh merged-main native recordings

[Sanitized native receipts](acceptance-surfaces-native-2026-11-12.json) record clean
source `5b5fe08` with tree digest
`eaf38b8ff6a081013252faf9f4d59c6eeb10c14881c916f9c93b5662e8d52802`.
Claude Code 2.1.322 passes all implemented CLI-print scenarios, including main and
detached native denial. Codex 0.167.2 passes all implemented ordinary-config linked
scenarios except main denial, so its aggregate remains BLOCKED. Both recordings
retain actual hook events and per-source hashes with an explicitly fixture-only
observer. The newly created Codex linked fixture is preserved on its original branch
with intentional probe changes; it must not be reused as a clean source worktree.

Two fresh Claude CLI-print suites also ran concurrently in separate disposable
repositories, both PASS, with 34.565 seconds of overlapping invocation windows.
Each completed discovery, exact edits, diagnostics/non-mutation and main/detached
denial. This establishes concurrent independent-repository sessions, not linked
worktree concurrency or interactive/Desktop behavior. The receipt records the
source snapshot with documentation WIP hashes separately from clean-main recordings.

A genuine Claude interactive terminal launch (without `-p`) reached the native
folder-trust prompt in a new independent fixture. The default “No, exit” was
selected; exit 1 and unchanged `ordinary.txt` confirm no edit scenario ran. This
is a concrete access prerequisite, not a native-hook failure or an interactive
acceptance pass. An initial invocation rejected `--no-session-persistence` because
that option only supports print mode; retry omitted it. No trust was granted.
The dedicated Copilot review request on PR #31 returned HTTP 422 with
`failure_reason: ACTOR_INELIGIBLE`, matching the prior failure on #30.
