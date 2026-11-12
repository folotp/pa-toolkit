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
| `specifications` | Official skills-ref API, vendored official schema, explicit Claude profile and online drift detection |

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

`./scripts/dev spec-freshness` downloads public data only, compares reviewed hashes
and stable publication status, and fails on drift, HTTP failures or unavailable
network. A higher working draft is not a published release. Full-page hashes
intentionally detect editorial changes as well as normative changes; they can
require maintenance without a validator change. There is no automatic repinning or
execution of downloaded source. Local/index/full/main/release checks include this
gate. Weekly and manually dispatched CI also run full validation.

To refresh a failed contract:

1. Run `./scripts/dev spec-review` for candidate URLs, hashes and byte counts. It is
   read-only and is not a successful freshness result. Fetch/read the affected
   official page separately; do not execute downloaded code.
2. Review normative fields, types, layout and upstream validator/dependency changes
   against the adapter and pinned official implementation. Keep intentional local
   restrictions explicit. When no old page bytes are available, review the current
   contract; do not claim to have identified the exact editorial diff.
3. Update only reviewed inventory entries/date in
   `tools/pa-devtools/src/pa_devtools/vendor/specifications.json`. For code/schema
   changes, update dependency pin/lock or vendored schema/license together with
   applicable regressions and docs. Never run the old recovery prototype as a fix.
4. Run specs, freshness, full and actual-index checks and review the normal PR diff.

On 2026-11-12, the Claude skills page's hash differed from the 2026-11-10 inventory.
The current frontmatter and external-distribution sections were reviewed; existing
supported fields remain valid. Its full-page hash was refreshed without expanding
the accepted field set or changing skills-ref. The subagent reference was added to
cover agent field predicates. No exact old/new page diff is claimed.

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
Doctor, specs, online freshness, links, inventory and package-contract remain required.
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
