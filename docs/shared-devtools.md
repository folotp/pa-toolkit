# Shared pa-devtools SDK and conservative CI

## Ownership and installation

`tools/pa-devtools` is the authoritative reusable Python package, version 0.1.0.
Toolkit is its first consumer. It is development infrastructure, excluded from the
runtime `.plugin` allowlist; it is not published on PyPI or installed by a plugin
release. Toolkit's launcher selects its own source; managed checks additionally use
`uv sync --locked` and the editable path in `pyproject.toml`. No adjacent repository
or installed Claude/Codex plugin cache supplies the implementation.

The dependency additions are official `skills-ref` at commit
`83021e2be457a9b6679148719c1f6074f0ad975e`, jsonschema 4.25.1 and pinned Hatchling
1.27.0 for building the SDK. PyYAML and markdown-it-py move to the SDK's optional
`checks` extra. Root `uv.lock` locks transitive checks dependencies. Launcher helpers
use Python 3.9+ stdlib; managed checks require the repository's Python 3.11+ environment.

| Module | Contract |
| --- | --- |
| `source` | Strict duplicate/nonfinite JSON, duplicate-safe YAML, version banners and relative Markdown links |
| `snapshots` | Actual-index export and isolated Git subprocess environment; caller owns branch authorization |
| `hooks` | Native edit path normalization and all-destination installation preflight; caller owns recognized bodies and path policy |
| `planning` | Declarative gate execution, complete Git diff, conservative impact selection and hosted baseline proof |
| `specifications` | Reproducible baseline, explicit Claude profile and optional frozen-inventory audit |
| `live_specs` | Current official revision/publication resolution, live schema/reference validation and provenance |

Adapters provide repository paths, gates and policy; the SDK never guesses a sibling
checkout or embeds vault, finance, protected-reference or marketplace rules. The
generic release driver/runbook stays authoritative for release orchestration.

Build independently with `uv build tools/pa-devtools --out-dir /explicit/output`.
A wheel includes the schema, inventory, NOTICE and Apache-2.0 license. Install the
wheel in a separate environment and validate resources/metadata before adoption;
editable-install success alone does not verify distribution. The SDK's version is
separate from `.claude-plugin/plugin.json`, which remains the runtime version SOT.

## Specification profiles and reviewed refresh

`./scripts/dev specs` checks raw YAML/types and repository invariants, invokes the
real `skills_ref.validator.validate_metadata` on core metadata, and validates
manifest fields through the vendored official Agent Plugins 1.0.0 JSON Schema.
Claude extension fields are checked explicitly before projection. Allowed-tools
arrays become text only in that projection; every adaptation is reported. Unknown
fields fail until intentionally supported. This is a supported subset of Claude's
fields, not an exhaustive schema for all present/future client features. Plugin
agents reject `permissionMode`, which Claude ignores for plugin subagents.

Claude mode adds `$schema` only to a temporary manifest object. It certifies field
validation with that reported adaptation, not portable package layout.
`./scripts/dev specs --profile portable` intentionally fails for this legacy package
(the actual manifest lacks `$schema`; release skills also have Claude extensions).
Do not remove supported Claude fields or migrate the manifest to make an audit green.
Official normative text: [Agent Skills](https://agentskills.io/specification),
[Claude skills](https://code.claude.com/docs/en/skills),
[Claude plugin reference](https://code.claude.com/docs/en/plugins-reference),
[Claude subagents](https://code.claude.com/docs/en/sub-agents), and
[Agent Plugins](https://github.com/agentplugins/agent-plugins-spec).

### Live authoritative specifications

`./scripts/dev spec-live` is a required gate on local full/index checks, PRs,
main, scheduled/manual CI and release preflight. It reads
`config/specifications.json`, resolves the official Agent Skills and Agent Plugins
repositories' current HEADs online, reads the publisher's current-published-release
statement, and downloads that version's schema from the resolved immutable revision.
A higher working draft is not selected. There is no hard-coded latest version.

It validates manifest fields against that newly fetched schema, using the schema's
declared supported JSON Schema dialect. Claude mode reports its temporary current
`$schema` envelope; it still does not certify a portable package layout. Skill
metadata has only explicitly supported Claude extensions projected out and tool
arrays normalized; unknown core fields reach the official validator. The current
`skills-ref` is installed by uv from the newly resolved official commit into an
isolated invocation environment and executes with credentials removed. This is
upstream executable code from the configured official authority, not downloaded
code treated merely as data. Official validator/dependency changes apply immediately;
network, installation, changed API/schema or new requirement failures fail the gate.
No pinned/cached success result substitutes; uv may cache immutable source/dependencies.

The live authority catalogue also fetches current Agent Skills, AGENTS.md, Claude
skills/plugin/subagent, Copilot instruction and Antigravity rule guidance. Prose-only
sources are recorded with URL/hash and explicitly labelled semantic **MANUAL_REVIEW**.
A fetched page proves availability, not automated natural-language compliance.
Repository-specific instruction separation, naming and governance checks remain
separate policy, not an invented official schema. Toolkit has no marketplace manifest:
marketplace conformance is NOT APPLICABLE here; consumer marketplace adoption must
use the relevant current official marketplace contract and its authoritative validator.

CI retains `official-specifications-*` JSON artifacts with resolved revisions,
published schema version, source URLs/hashes, adaptations, results and limits.
`PA_SPEC_REPORT` selects an external receipt path; stdout also retains provenance.
Receipts are evidence, never cross-run release attestations or skip authorization.

The original pinned skills-ref/schema still supports reproducible local baseline
validation and catches stricter repository policy. `spec-freshness` remains an
optional frozen-inventory drift audit; `spec-review` reports candidate hashes without
writing pins. Neither stands in for the required live check. Editorial changes to
prose no longer require repinning merely to unblock CI; changes needing adapter or
policy updates still require normal tests/docs/PR review. Do not auto-rewrite the
legacy manifest, user invocation controls or protected content.

## Selective CI trust and execution

`config/development.json` is the declarative gate/impact source. `scripts/dev plan
--base <SHA>` explains selection. `scripts/dev ci --base <SHA>` requires a clean tree
and executes that plan. Reduction requires all of the following:

- A complete Git diff against an ancestor base; renames include old and new names.
- Every baseline policy path exists and is unchanged, including engine, adapter,
  gates/tests, configuration, workflow and dependency locks.
- The GitHub API reports a completed successful **main push** for that exact SHA,
  repository and workflow. A local flag, receipt, PR run or other workflow cannot
  substitute. API/history/policy failures select the full path.

Known docs-only and runtime metadata/version changes omit unaffected code/tests.
Doctor, baseline specs, live official specifications, links, inventory and package-contract remain required.
Runtime changes still build and verify the real allowlisted ZIP; development docs
with unchanged runtime inputs omit archive generation. Code paths select lint/tests;
engine, gate policy, tests, workflows and unknown paths force full validation.
The first PR cannot reduce against main without this compatible policy.

CI checks out complete history and compares the actual merge result with the PR base
SHA. Both protected `Release checks (ubuntu-latest)` and `Release checks
(macos-latest)` always report; there is no workflow path filter. macos-latest's
protected name still selects macos-15 and asserts ARM64/arm64. Token permissions are
read-only contents/actions. Fork/API limitations cause full validation.

Main pushes, schedule/manual runs and `--full` unconditionally use the generic
release driver, one full extension preflight and a real archive dry-run. Release
preflight never calls the selector or reuses PR evidence. This does not implement
cross-run release attestation reuse or issue #20's release-depth UX.

## Organon and marketplace adoption plan

Both reference repositories are read-only during this implementation. Organon's
current engine duplicates parsers, index isolation and hook mechanics; its provenance,
protected-reference, connector, token and vault rules remain domain-owned. Marketplace
#13 needs its existing online validator, protected bot workflow and pin policy kept
intact. Do not run its real bumper, change manifests, or modify its named preserved
stash while testing shared infrastructure.

After this SDK is merged through its own PR, each consumer can adopt in a separate
authorized PR. Select an exact reviewed **merged** toolkit commit, never this feature
branch, a moving tag, or a filesystem sibling. Use a Git dependency shaped as
`pa-devtools[checks] @ git+https://github.com/folotp/pa-toolkit@<merged-40-char-SHA>#subdirectory=tools/pa-devtools`,
lock transitives and install through that consumer's managed environment. For Python
3.9 launcher operations before optional checks dependencies exist, bootstrap the SDK
wheel without extras into an explicit ignored tooling environment from the same pin;
use its Python for index/hooks. Do not silently fall back to a monolithic copy.
Document bootstrap/cache/network failure remedies in the consumer PR.

Move only generic implementation calls to the SDK; retain thin client adapters and
repository-specific gate functions/configuration. Compare behavioral fixtures before
removing duplicates, then verify index isolation, unmanaged hooks, fresh client
behavior when bindings change, wheel resources, runtime exclusion and required CI.
Enable reduction only after a compatible full main baseline exists. Roll back by
restoring the prior reviewed SDK SHA/lock through a normal PR, preserving protection.
This is an adoption contract and plan, not a claim that consumers are migrated or a
public SDK artifact exists.

Verification and limitations are recorded in the [SDK report](verification/shared-devtools.md).
