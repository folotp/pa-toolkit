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

Codex CLI 0.167.0 previously selected hook definitions from the primary checkout when
started in a linked worktree. Inspect `/hooks` and review/trust exact definitions.
Do not change global trust/project settings to test new definitions. The current acceptance runner never bypasses hook trust or changes global/project
trust settings. Missing native event delivery is BLOCKED and retains the actual
Git/index/CI fallback. Earlier 2026-11-10 invocation-local trust-bypass recordings
are historical and do not certify this no-bypass acceptance route. After merge,
update primary main so ordinary discovery sees the tracked adapters. See the
[reusable plan](agent-test-plan.md) and [current report](verification/supported-agents.md).


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
