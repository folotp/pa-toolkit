# Shared SDK and selective-CI verification

Date: 2026-11-12. This extends the earlier
[client lifecycle evidence](shared-ai-setup.md); those recorded client versions and
source hashes describe the earlier implementation. No fresh native client-delivery
run is claimed for this extraction. Event bindings and payload semantics are unchanged;
existing path, hook, index and feedback regressions run against the extracted helpers.

The temporary implementation checkout was absent at resume. Every durable backup
checksum passed. A new named `feat/agent-neutral-development-recovery` worktree was
created at 412fc97 and all sixteen WIP sources matched their recorded SHA-256 before
further edits. The original branch and backup were retained. No task-owned processes
remained at the initial audit.

## Current validation

- `uv sync --locked` succeeds from the recovered path, with official skills-ref at
  the recorded exact upstream SHA. The old E402 failure is resolved by importing
  the installed SDK normally in tests, without an import waiver.
- `./scripts/dev check` passes all declared gates, including **63 unit/integration
  tests**, official skill/schema validation, nine-source live freshness, Ruff,
  shell checks, actionlint, links, inventory and runtime package contract.
- Tests exercise actual workflow shell routing for PR/main/schedule, real adapter
  planning and selected command dispatch for docs/version/runtime-code changes,
  required structural gates, archive decisions and unconditional full non-PR CI.
  Controlled hosted-response fixtures cover exact-main proof, missing/API/malformed
  failures, changed policy/engine directories, nonancestor bases and complete rename
  impact. These are isolated fixtures, not successful hosted reduced-run evidence.
- `uv build tools/pa-devtools --out-dir <external-output>` produces sdist and wheel.
  Installing that wheel with `[checks]` into an independent environment and importing
  with `python -I` verifies all shared modules, four vendored resources, the official
  skill validator and adapted manifest-schema validation outside source loading.
- System Python 3.9.6 with `-I` imports all shared modules and reads pins/resources
  without optional dependencies; the full managed gate uses Python 3.11.18.

Run `./scripts/dev check --staged` after staging the intended source, and use the
unchanged generic driver from a clean committed checkout for a real archive dry-run.
Commit/push hooks enforce their existing contracts; no bypass is part of verification.
Current-head hosted Linux and macos-15 ARM64 outcomes must be read from GitHub after
push. Prior successful 412fc97 jobs validate only that earlier baseline.

## Explicit limits

Main does not yet contain a compatible policy baseline. PR #24 must run full CI;
a real reduced hosted run cannot be demonstrated against a successful compatible
main-push baseline before merge. Fixture evidence proves routing/selection, not that
a future GitHub job has skipped work. No merge is authorized to manufacture proof.

Strict portable audit remains intentionally failing for the legacy manifest and
Claude-only release-skill metadata. No runtime version, public SDK publication,
marketplace pin or reference repository was changed. SDK adoption by Organon and
marketplace remains the separately reviewed plan in the [SDK contract](../shared-devtools.md).
