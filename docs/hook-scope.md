# Development lifecycle hook scope

These bindings are source-only development adapters. None ship in the plugin archive.
The [shared architecture](development-architecture.md) and [setup/recovery](development.md)
cover mandatory Git/CI gates; [verification](verification/shared-ai-setup.md) records
actual fresh-client observations separately from parsed configuration.

## Shared behavior

Both clients bind SessionStart, PreToolUse, PostToolUse and Stop to `scripts/dev hook`.
Commands resolve `git rev-parse --show-toplevel` at execution time, so payload cwd,
linked checkout and subdirectory launches select the active worktree implementation.
No adapter copies policy or uses an adjacent checkout. The launcher normalizes client
startup to its own root, preserving argv/trust/sandbox options.

- SessionStart emits JSON context identifying the active root/branch and shared gate.
- PreToolUse normalizes all native edit paths and rejects main/detached edits and
  malformed/outside-root payloads with stderr and exit 2. Toolkit has no immutable
  reference inventory, protection token or special restriction on ordinary files.
- PostToolUse returns bounded JSON additionalContext, at most 4000 characters, with
  Python/JSON syntax or shell formatting/lint feedback. It never rewrites source.
  Missing tools/errors produce explicit advisory-unavailable feedback.
- Stop returns bounded systemMessage shell lint advice, exit 0, and skips when
  `stop_hook_active` is true. It never returns a continuation/block request or
  additionalContext that would induce a recursive Stop cycle. Full tests stay explicit.

The lightweight adapters use launcher Python 3.9+ and external shell tools without
syncing managed dependencies. Required staged/CI checks use locked managed Python.
A native PreToolUse failure blocks the call; post-edit and Stop advice are advisory.
Git rejects main/detached commits and validates staged bytes regardless of editor.
Pre-push checks remote destinations, including feature-to-main updates and deletes.

## Payloads and surfaces

Claude matches `Edit|Write|MultiEdit`; these provide `tool_input.file_path`.
NotebookEdit, arbitrary shell/MCP writes and future renamed tools are outside this
matcher. The binding/normalizer regression test catches local drift only; it cannot
discover a new upstream tool. Add a reviewed payload contract and native test before
expanding coverage. MultiEdit was not exposed in the recorded cloud session.
Use one session per checkout: commands find the session's Git root; editing a
second worktree from that session is rejected as outside-root even if that other
worktree has an allowed branch. Start a new session in the intended checkout.
Codex matches `apply_patch|Edit|Write`; native apply_patch supplies its full patch in
`tool_input.command`. Central normalization includes every Add/Update/Delete/Move-to
header; move destinations cannot escape checking. Relative paths resolve against an
absolute payload cwd, dot segments and symlinks are resolved, and paths outside the
active root fail. These are edit-path checks, not a full patch grammar implementation.
Tool execution remains responsible for patch validity.

The installed Codex 0.167.0 code-mode host delivered canonical apply_patch hooks
even when the native patch was invoked through functions.exec; that specific path
was verified with a real two-file patch. Arbitrary shell writes, MCP writes, other
nested orchestration and hosted/cloud editing paths are outside the verified scope. Native repository hooks on those surfaces are unverified.
Use mandatory Git index checking and required Linux/macOS CI for every committed path.
No claim of hook coverage follows from configuration parsing, user trust or a model's
statement that advice changed the file: inspect actual event delivery and file bytes.

Codex CLI 0.167.2 was rechecked on 2026-11-12: read-only `hooks/list` selects
primary-checkout definitions for linked root/subdirectory launches. Existing trusted
definitions delivered actual native start/edit/feedback/stop events, both path-specific
diagnostics and detached denial in the selected disposable worktrees. The independent
ignored-user-config fixture has a disabled project layer and no project hooks; that
route remains BLOCKED. No trust or sandbox bypass was used. Main native denial remains
BLOCKED because primary main is preserved. See the [current evidence](verification/acceptance-cli-2026-11-12.md).

Use `--codex-fixture` only with a newly created, clean, explicitly disposable linked
`chore/acceptance-codex-*` checkout. The runner retains normal existing configuration,
never grants trust, refuses changed source/primary hook bindings and preserves the
fixture and original branch. Review changed definitions in the client when needed;
do not manufacture a pass by copying trust or changing global project settings.
Earlier 2026-11-10 bypass-assisted recordings remain historical. Shell/MCP paths and
other surfaces retain Git/index/CI enforcement; no native claim follows from those gates.


## Official contracts

Rechecked 2026-11-10:

- [OpenAI lifecycle hooks](https://learn.chatgpt.com/docs/hooks?site_variant=chatgpt):
  repo-local hooks, native tool_input.command, JSON context and invocation-local trust.
- [Claude hooks reference](https://code.claude.com/docs/en/hooks): file-tool inputs,
  exit 2 PreToolUse blocking, event-specific JSON context and Stop loop semantics.
- [Claude memory discovery](https://code.claude.com/docs/en/memory): canonical import.
- [Claude skill reference](https://code.claude.com/docs/en/skills): legacy supported fields.
- [Anthropic skill authoring guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices):
  structural field boundaries versus the broader semantic audit tracked in #14.


## Opt-in invocation receipts

Set `PA_TOOLKIT_HOOK_TRACE` in the environment inherited by a fresh client to an
absolute path to an **existing private regular file outside the checkout**. For
example, after choosing an external directory you own:

```sh
(umask 077; touch /absolute/external/events.jsonl)
chmod 600 /absolute/external/events.jsonl
export PA_TOOLKIT_HOOK_TRACE=/absolute/external/events.jsonl
./scripts/dev session claude
```

For cloud, use a task-private external scratch directory and the environment's
supported setup mechanism before launching the acceptance session. Do not assume
an export in an agent's child shell propagates back to its already running client.
No project setting or trust is changed by recording. Unset the variable for normal
work; no file is created by the adapter. Final symlinks, hard links, non-regular
files, files readable by other users and files owned by another uid are refused.
macOS/Linux append locking serializes concurrent writers. Lock acquisition retries
for at most 0.25 seconds; contention then reports an unavailable receipt and retains
the hook result instead of waiting for the client timeout.

Each JSONL record contains UTC time, toolkit event (`start`, `edit`, `feedback`,
`stop`), an allowlisted native tool name (otherwise null), CLI exit code and outcome
(`completed`, `rejected`, `advisory_unavailable`, or unexpected `error`). No payload,
file path/content, diagnostic, prompt or configuration is retained. Feedback/Stop
errors retain their existing advisory exit 0; edit/start errors retain exit 2.
Repeat Stop suppression is recorded as completed without emitting advice. An
unwritable/unsafe trace destination emits a stderr remedy and preserves the hook's
original result. Invocation receipts are optional and never a gate dependency.

A manual `scripts/dev hook` invocation writes the same receipt, so a receipt alone
cannot establish native delivery. Pair it with the exact client/version/session,
source hashes, actual tool call, visible diagnostics and target bytes. Missing
records leave delivery unproven. The existing disposable CLI observer still records
bounded diagnostics separately and remains explicitly fixture-only. These receipts
have deterministic coverage and [fresh local CLI delivery](verification/linked-acceptance-2026-11-12.md).
Desktop/cloud delivery is still required on those selected surfaces.

## Claude cloud limits and external hooks

The consolidated [cloud report](verification/native-results-followup-2026-11-12.md)
records native Edit/Write feedback and detached denial on 1e0a7f6. It exposes selected
context/errors, not raw hook inputs or exit codes. Toolkit Stop delivery remains
unwitnessed there. PostToolUse context cannot require an agent to fix a defect;
Git/index checks and required CI are the committed-change enforcement layers.

Environment-level hooks can coexist with repository hooks. A Stop request to commit
intentional fixtures does not override the acceptance task: preserve byte-identical
external evidence, report the conflicting hook, and do not commit defects. Do not
disable a hook or delete a live fixture without authorization. A manual Stop call
or absence of later advice does not prove the repository Stop adapter ran.
