# Agent-neutral development architecture

[AGENTS.md](../AGENTS.md) is the canonical human/agent contract. Root CLAUDE.md imports
it; Codex discovers it directly. [Setup and recovery](development.md),
[client scope](hook-scope.md) and [acceptance evidence](verification/shared-ai-setup.md)
complete the operational contract. Update implementation, source contracts, tests
and documentation in the same PR. No private memory or conversation is required.

## Ownership and data flow

| Authoritative source | Responsibility |
| --- | --- |
| `scripts/dev`, `scripts/dev.py` | Checkout resolution, command dispatch, deterministic checks, index isolation, hook adaptation, diagnostics and toolkit package selection |
| `config/toolchain.json`, `.python-version`, `pyproject.toml`, `uv.lock` | Supported executable minimums, managed interpreter and pinned/hash-locked Python dependencies |
| `specs()` / `frontmatter()` in `scripts/dev.py` | Strict YAML, supported legacy Claude schemas and toolkit component invariants |
| `config/package-files.json` | Explicit tracked runtime file inventory; new files require a review decision |
| `config/release.json` | Toolkit extension selecting shared check and package commands |
| `skills/plugin-release/scripts/release.py` and [shared runbook](../skills/plugin-release/references/runbook.md) | General release identity, extension/fallback selection, archive receipt and publication sequence |
| `skills/plugin-release/scripts/package.sh` | Low-level generic ZIP writer; never the standalone release preflight |
| `skills/plugin-release/scripts/branch-guard.py` | Reusable destination-aware main push policy and legacy generic guard installer |
| `.claude/settings.json`, `.codex/hooks.json` | Optional development event bindings; no independent policy implementation |
| `.github/workflows/release-checks.yml` | Linux/macOS full gate and real release dry-run; required status names stay stable |

```mermaid
flowchart TD
    H[Humans and agents] --> D[scripts/dev check]
    A[Client lifecycle adapters] --> F[Shared bounded feedback]
    G[Git pre-commit] --> I[Export actual index to isolated repository]
    I --> D
    C[Linux/macOS CI] --> R[Generic release driver]
    R --> E[Toolkit release extension]
    E --> D
    E --> P[Explicit runtime staging and real ZIP verification]
    R --> J[Explicit archive receipt]
```

`check()` runs diagnostics, component schemas, shell/Python/CI lint and format
verification, Markdown links, README inventory, package-contract/link closure and
all infrastructure tests. Required failures stop execution. Format is an explicit
write operation. Lightweight client feedback checks syntax/shell style; it does not
replace the complete gate. The Git index and CI independently cover shell/MCP/hosted
writes outside native edit matchers.

## Reuse and intentional differences from Organon

The architecture and stable generic patterns are adapted from Organon main
`c5a9cd8fabd2af5459ea073850204caa70ae9ad7`: self-resolving launcher, isolated index,
Git-resolved hooks, bounded lifecycle feedback, Markdown parsing, explicit package
selection and archive verification. The code is maintained here with local tests;
there is no runtime adjacent-checkout dependency or new shared-engine project.
General release orchestration is reused directly from this repository rather than
copied. Generic push protection has one implementation, imported by scripts/dev.

Toolkit-specific validation preserves `.claude-plugin/plugin.json` version ownership
and Claude-only skill fields (`argument-hint`, `disable-model-invocation`, YAML tool
arrays). Organon's root-manifest/symlink schema and skills-ref portability restriction
are inapplicable. New unsupported fields fail until their contracts and tests are
reviewed. See [schema boundaries](development.md#component-and-source-gates).

Kepano provenance pins, protected references, resync tokens, connector inventories,
vault lints, commands/Gemini bundles and token-scenario baselines are absent from this
repository. Inventing such gates would provide no evidence about its contents.
Skill wording, trigger quality, domain behavior and performance remain review/live
test concerns under #14; no synthetic token budget is represented as measured usage.

## Index and hook contracts

The staged checker rejects main/detached HEAD and unmerged indexes, writes the staged
Git tree, exports staged bytes/modes, initializes a temporary repository, fetches
committed HEAD and reads the staged tree into its isolated index. An object alternate
provides staged blobs without modifying the real index. Inherited `GIT_*` variables
are stripped for all isolated subprocesses. Both staged and unstaged whitespace checks
run there. An unstaged repair cannot hide malformed staged content. Temporary storage
is cleaned on success or failure; neither the branch nor source files are changed.

Installation preflights both hook destinations before writing either. Relative or
absolute `core.hooksPath` and shared linked-worktree metadata are resolved by Git.
Exact generated v1 launchers and exact legacy toolkit branch-guard bodies are the
only automatic migration inputs. Marker substrings do not authorize replacement.
Unmanaged files and final hook symlinks are preserved. New launchers resolve the
invoking worktree at event time, never the installation checkout. Pre-push delegates
to the generic destination guard, including deletes and multiple updates. Old
worktrees without scripts/dev fail with an update/recovery instruction.

Local hooks are not a security boundary. Git options can bypass them; independently
required protected-main CI is the merge boundary. Installation is not a CI dependency.

## Packaging and release

The allowlist names regular tracked files individually. Arbitrary new/untracked files
inside a runtime directory are excluded. Missing, duplicate, unsafe, development,
local-artifact and symlink inputs fail. All runtime skills, agents and shared release
resources must remain selected. Runtime Markdown links are checked against staged
payloads, so omitted linked resources fail before building. Source-only development
links use repository URLs in shipped documentation.

The generic extension executes `release-check` once (clean tree plus full gate), then
`package` (private staging, low-level packager, exact ZIP inventory/integrity/source-byte
verification). This avoids duplicate heavy gates **within the same invocation**;
it does not reuse checks from earlier commits or a bump PR. Both release-driver modes
verify a real archive. Output and JSON receipt stay outside source. Exact merged
remote-main verification remains mandatory in the general runbook before tagging.
No release request is implied by implementation or CI.

The fallback remains available to other repositories without an extension. An existing
malformed extension fails closed, including nonobjects, boolean schema versions,
empty commands and broken symlinks. One-pass placeholder replacement, literal braces,
explicit archive receipts and failure propagation retain regression coverage.

## CI ownership and maintenance

The existing `Release checks (ubuntu-latest)` and `Release checks (macos-latest)`
contexts run the full release dry-run on PRs and main pushes with read-only permissions.
The extension reaches the same `check()` as local/index use, then verifies a real ZIP.
No local hook, AI client, vault, finance account or personal data is needed. uv 0.13.7
and managed Python 3.11 are selected; shell tools enforce supported minimums. Linux
bootstraps actionlint v1.7.7 with Go; Go is not a project/runtime gate. macOS uses
Homebrew actionlint. Python transitive dependencies are hash locked.

Server protection is separate: PRs, strict required matrix checks, admin enforcement,
no force pushes/deletion. Never rename a required context without coordinating the
server migration. Current live readback is recorded in the acceptance report.

| Change | Update together | Verification |
| --- | --- | --- |
| New check/schema field | Shared function, docstrings, schema boundaries, fixtures | Failure/pass regression, full gate and index check |
| Dependency | Exact pyproject requirement, uv lock, tool policy, CI/bootstrap docs | Locked sync, missing/old/cache failures, both OS checks |
| Native event/payload | Central normalization, thin bindings, hook scope | Payload tests **and** fresh client delivery/feedback evidence |
| Runtime resource | Explicit file inventory and owning skill/agent documentation | Contract/link closure and actual archive equality/bytes |
| Release behavior | General driver/runbook and consumer extension only as needed | Both modes, fallback, errors, braces and receipts |
| Hook lifecycle | Installer/body recognition and recovery docs | Unmanaged/shared/custom-path and old-branch tests |

Recovery procedures belong in [development.md](development.md). Issue coordination
and remaining client limits belong in the tracked [report](verification/shared-ai-setup.md).
