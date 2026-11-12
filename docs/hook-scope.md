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
