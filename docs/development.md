# Development setup and recovery

Read [AGENTS.md](../AGENTS.md), [architecture](development-architecture.md) and
[hook scope](hook-scope.md). Source and installed marketplace plugin copies are distinct.
Changing this checkout does not publish or update installed plugins.

## Reproducible setup

Required minimum executable versions are in `config/toolchain.json`: Git 2.31,
uv 0.13.7, Bash 3.2, jq 1.6, Zip 3.0, UnZip 6.0, shfmt 3.6, ShellCheck 0.9 and
actionlint 1.7.12. Git supplies archive/tree transport; no standalone tar command is
used by the toolkit extension. The generic release fallback still requires tar.
Claude, Codex, GitHub CLI and Go are optional development/session/bootstrap tools,
not required content checks. Publication separately needs GitHub authentication.

Launcher `python3` must be 3.9+. uv selects managed Python 3.11 using `.python-version`;
the project supports Python 3.11-3.15. Do not reject Apple's launcher Python just
because it is older than managed Python. Doctor prints the executing interpreter
and independently probes the managed interpreter/imports. PyYAML 6.0.3,
Markdown-it-py 4.2.0 and Ruff 0.14.10 plus the mdurl transitive dependency are exact
and hash-locked in `uv.lock`. No skill-reference, JSON-schema, tokenizer, Node, vault
or finance dependency is needed for these actual gates.

macOS bootstrap (Homebrew):

```sh
brew install uv jq shfmt shellcheck actionlint
uv sync --locked
./scripts/dev doctor
./scripts/dev check
```

Linux bootstrap (Ubuntu 24.04 or newer):

```sh
sudo apt-get update
sudo apt-get install -y git bash jq zip unzip shfmt shellcheck
# Install uv 0.13.7 using Astral's official installation method.
# Install actionlint >=1.7.12 using its official release binary, or with Go:
go install github.com/rhysd/actionlint/cmd/actionlint@v1.7.12
# Put the chosen actionlint binary on PATH.
uv sync --locked
./scripts/dev doctor
./scripts/dev check
```

See [uv installation](https://docs.astral.sh/uv/getting-started/installation/) and
[actionlint installation](https://github.com/rhysd/actionlint/blob/main/docs/install.md).
CI declares the same dependencies in the workflow. OS tools use supported minimums,
not a claim of identical package-manager versions on both platforms. Locks cover
Python dependencies; uv's selected interpreter download is independently managed.

Missing tools, unknown/unsupported versions and unavailable required checks fail.
A blocked cache or network is not a skipped pass. Request approved access where
required, or explicitly provision a writable per-invocation `UV_CACHE_DIR` and
`UV_PROJECT_ENVIRONMENT` with the locked dependencies. Do not change global settings,
disable the sandbox or remove gates to make diagnostics green. Offline use requires
an already populated permitted cache/environment (`uv sync --locked --offline`).
The lightweight hook paths do not sync dependencies or make network requests.

## Local checks, hosted CI and specification versions

Local `scripts/dev check`, the installed staged Git hook and hosted CI all reach
one `check()` implementation. The staged hook exports the actual Git index first.
For the exact hosted scope locally, run the release-driver dry-run from a clean
checkout with output/receipt paths outside source (see the release example below).
The driver selects `config/release.json`: full check once, then a real archive.
Normal `scripts/dev check` verifies the package selection/link contract without
creating that archive. OS-specific bootstrap steps are declared in the workflow.

Hosted macOS uses explicit `macos-15` Apple Silicon and verifies reported/actual
ARM64 architecture before checks. The required historical status context remains
`Release checks (macos-latest)`. No Intel fallback masks a capacity failure.

GitHub independently reruns checks on PR updates and main pushes. A successful local
run does not publish a GitHub check status or replace either required hosted result.
Dependency caches may avoid downloads; they are not trusted test-result receipts.
No cross-machine/cross-commit validation reuse is implemented here; #20 remains
separate and cannot weaken exact-commit release verification.

The mandatory component gate is a repository-owned, reviewed Claude-compatible
contract in `scripts/dev.py`, with strict YAML/JSON and supported field predicates.
It does **not** fetch upstream specifications on each run or assert compliance with
whatever is newest upstream. It also does not apply the portable Agent Plugins
schema to this legacy Claude manifest. Optional `claude plugin validate` tests the
installed client version and is not a mandatory/latest-spec certification.

A future upstream-spec update/drift check needs explicit source versions, an update
policy and compatibility profiles. The official
[Agent Skills specification](https://agentskills.io/specification),
[Agent Plugins specification](https://agent-plugins.org/),
[Claude skills reference](https://code.claude.com/docs/en/skills) and
[Claude plugin manifest reference](https://code.claude.com/docs/en/plugins-reference)
are separate contracts. Keep the existing Claude invocation controls/tool arrays
and `.claude-plugin/plugin.json` source until an intentional migration is reviewed.
#14's broader skill-guideline audit is still separate from structural validation.

## Worktrees and sessions

```sh
./scripts/dev worktree feat/example /explicit/disposable/path
cd /explicit/disposable/path/scripts
./dev session claude
# Or ./dev session codex [client arguments]
```

Worktree creation starts a new named branch from local main; fetch/verify main before
using it. Destination is explicit and existing paths/branches fail through Git.
Each editing session owns its branch/worktree. The launcher changes only its child
process cwd to its own root and passes client argv unchanged. It grants no trust or
permissions, installs no plugin and never switches another checkout's branch.
For clients started directly in a subdirectory, discovery varies; use the launcher.
Review project hooks in the client before relying on them.

## Commands

| Command | Contract |
| --- | --- |
| `scripts/dev doctor` | Required versions, managed Python/import readiness and advisory local hook state |
| `scripts/dev check` | Full shared gate including all infrastructure tests |
| `scripts/dev check --staged` / `check-staged` | Full gate on actual exported index; reject main/detached/unmerged index |
| `scripts/dev format` | Explicit shfmt/Ruff formatting of all selected shell/Python source |
| `scripts/dev specs` / `links` / `inventory` | Focused structural diagnostics; not substitutes for check |
| `scripts/dev package-check` | Runtime selection and staged link closure, without a ZIP |
| `scripts/dev package --output /outside/source` | Real ZIP, exact entries/bytes; default packager is the explicit adjacent generic script |
| `scripts/dev release-check` | Clean-tree requirement plus full gate, selected by the release extension |
| `scripts/dev install-hooks [--uninstall]` | Safe shared/custom Git hook installation/removal |
| `scripts/dev worktree <branch> <destination>` | New feat/fix/chore/perf/docs branch and linked worktree |
| `scripts/dev session claude\|codex [args]` | Client launch at this checkout's root |

Run `python3 -m unittest discover -s tests -v` with the locked environment active before
committing release infrastructure changes (or `uv run --locked python -m unittest
discover -s tests -v`). `check` includes this exact suite using managed Python.
Normal check never rewrites source; explicit format is reviewed like any source change.
The initial style migration formats existing Python and package.sh rather than
excluding them from the gate. No validation defects are grandfathered silently.

## Component and source gates

- Skills/agents: strict SafeLoader YAML, duplicate-key rejection, nonempty body/name/
  description, path/name agreement, name length/kebab case, description limits and
  explicit field types. Release remains user-only; gatekeeper tools remain unpinned.
- Skills preserve documented Claude `argument-hint`, boolean invocation controls,
  string/array `allowed-tools`, model, context/agent, license/compatibility/metadata.
  Agent tools/disallowedTools, model/color, permissionMode, maxTurns, skills, memory,
  background and isolation have explicit predicates. New hooks/MCP sub-config fields
  are not silently accepted: add a tested contract before introducing them.
- Manifest: legacy location only, required identity/description, SemVer, author and
  keyword types, explicit optional metadata. No root migration or bundled `.mcp.json`.
- Markdown: parsed relative file/image/reference links, URL-decoded paths and package
  link closure. Code examples, remote URL availability, anchors and vault wikilinks
  are outside this gate. Skills' inline example vault paths are not filesystem links.
- Inventory: exact README current skill/agent lists and canonical CLAUDE.md import.
- Code: Bash syntax, shfmt 4-space/case-indent, warning-level ShellCheck, Python AST,
  Ruff format/lint (E4/E7/E9/F), strict JSON configuration and actionlint for all workflows.
  Git whitespace checks cover both index and working-tree diffs.
- Package: exact reviewed tracked-file allowlist, no symlinks or development/local
  paths, mandatory runtime resources, staged links and real ZIP equality/bytes.

These checks do not certify semantic finance operations or instruction quality.
The wider Anthropic guideline audit (#14) remains separate. All seven skills and
both agents are structurally gated; #10's ambiguous YAML description is corrected.

## Git hooks and protection recovery

Install only after understanding shared scope:

```sh
./scripts/dev install-hooks
```

Git resolves pre-commit and pre-push using the active repository's `core.hooksPath`.
Linked worktrees often share hooks. Both destinations are checked before either write;
exact managed toolkit branch-guard hooks migrate, custom hooks/symlinks remain intact.
Uninstall accepts only exact current launchers. It does not restore old guard bodies.
Back up an unmanaged hook yourself, then manually compose it with calls to the active
root's `scripts/dev check-staged` (pre-commit) or `scripts/dev pre-push` (pre-push).
Preserve exit failures. Pre-push stdin can be consumed only once: spool it to a private
temporary file and feed that file separately to each composed guard; remove it on exit.
Do not concatenate two stdin consumers or merely append after an `exec` line.

After installation an old worktree without scripts/dev fails closed. Update/rebase
that branch to the merged tooling before committing, or restore a reviewed previous
hook arrangement. Never use `--no-verify` to conceal failure. Our launchers do not pin
an implementation-worktree path; removing the installer checkout does not break them.
An unmanaged installer in another project must not replace these stronger hooks.

Required CI and live main protection remain independent. Repair broken tools/checks
through a feature PR; never weaken contexts, admin enforcement or exact merged-release
verification. After a squash revert, start from current main and inspect the actual
triple-dot PR diff before assuming old commits restore reverted content.

## Release verification and issue boundaries

From a clean linked worktree:

```sh
python3 skills/plugin-release/scripts/release.py . \
  --dry-run --output /explicit/outside/package \
  --result /explicit/outside/receipt.json
```

Build uses the same command without `--dry-run`; only that verified receipt's `archive`
path is eligible for a separately authorized upload. Dry-run archive is null.
The shared [release runbook](../skills/plugin-release/references/runbook.md) still owns
bump/PR, exact merged remote-main check, tag and publication. No CI publishes artifacts.

#19's generic direct-package.sh artifact policy remains separate: the toolkit extension
selects tracked allowlisted files before calling it. #20's cross-run heavy-check reuse
and release-depth UX remain separate; this extension runs the full gate once for every
exact invocation/commit. #18 marketplace dispatch redesign is unchanged. #13 historical
root archive cleanup is not performed; new release-driver output is explicit/outside
source. None of those issues is silently closed by this implementation.
