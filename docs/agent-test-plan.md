# Reusable development-agent acceptance plan

## Scope and evidence rules

Choose repository, exact source/dirty hashes, client product/version/surface, required
commands and explicit evidence output paths before a run. CI is a validation surface,
not an AI agent. Model credentials are never required by deterministic gates.

Use PASS / FAIL / BLOCKED / NOT RUN / NOT APPLICABLE. Retain actual native calls,
event exits/diagnostics, exact fixture bytes/hashes, process overlap, checkout changes
and cleanup limits. Configuration parsing, a model narrative or a manual hook call
cannot prove native delivery. Earlier runs do not certify later source by implication.
The [acceptance summary](acceptance.md) records historical coverage and owner decisions;
the [supported-agent contract](supported-agents.md) defines discovery and current routes.

Fixtures must be runner-owned disposable repositories or explicitly selected test
worktrees outside vault mounts. Preserve unrelated checkouts/indexes/settings. Do not
bypass trust, sandbox, permissions or protection, access personal connectors, activate
paid services or publish to obtain a passing result. Identify unavailable prerequisites
and leave dependent scenarios BLOCKED. Live-model testing is optional and purposeful;
repeat it for relevant changes or unresolved failures, not routine documentation edits.

## Scenario catalogue

| ID | Setup and operation | Expected evidence and failure behavior |
| --- | --- | --- |
| A01 | Start fresh at root, then through the session launcher from a subdirectory; add a fixture-only random marker to canonical instructions, not the prompt | Client returns loaded marker; launcher root and forwarded argv verified; instructions are regular files with one policy source |
| A02 | Native valid text edit in the disposable fixture | Only intended bytes change; record native tool and real before/after event delivery when supported |
| A03 | Native shell formatting defect and invalid JSON; leave intentional defects intact | Feedback identifies defects, remains bounded and never formats/repairs; compare exact resulting bytes |
| A04 | Native multi-file patch or multiple native edits | All paths checked/observed; each relevant feedback event is witnessed. A CLI lacking one-patch support records native sequential edits explicitly |
| A05 | Attempt one native edit on detached HEAD/main | Supported native pre-edit hook denies it and bytes remain unchanged. Do not prompt the agent to evade the guard; absent hook delivery is BLOCKED, not a pass |
| G01 | Invalid staged YAML with repaired working file, and valid staged bytes with invalid unstaged file | Actual-index checker rejects first and accepts second independently of working bytes |
| G02 | Main/detached commit guards, feature-to-main push, feature-to-feature push, multi-ref/deletion inputs | Expected destination and branch outcomes; no real main push or destructive ref update |
| G03 | Custom/shared/unmanaged/symlink hooks and incomplete install destinations | Respect Git hook location, preflight all writes and preserve unmanaged content |
| E01 | Two independent sessions/worktrees and subdirectory launches | Each stays on its own checkout/branch; no shared temporary filenames or cross-session modification |
| E02 | Missing/old prerequisite, unavailable network/cache or client authentication | Actionable failure/BLOCKED; no old success receipt or disabled gate substitutes |
| S01 | Resolve current official skill/reference-validator HEAD and current published plugin schema online | Validate actual metadata/manifest projection using those versions; record source URLs/revisions/hashes; newer published version applies without manual version edit |
| S02 | Official new required field or unavailable/ambiguous authority | New contract failure propagates; network/resolution failure cannot silently use vendored latest-pass |
| S03 | AGENTS.md, client guidance or marketplace formats with prose-only authority | Retrieve current official source; label semantic review limits. Do not invent an official schema or certify natural-language compliance from a downloaded page |
| P01 | Real archive or marketplace validation from clean exact source | Preserve authoritative inventory/validator, exclusion and receipt semantics; no publication |
| C01 | Implementation PR CI on Linux and macOS ARM | Both live required contexts pass for the selected commit; logs show executed gates, source-resolution evidence and actual archive where applicable |
| C02 | Docs-only/version-bump PR versus engine/workflow/unknown input | Omit only proven-unaffected gates after exact compatible main-push proof; full fallback otherwise; structural/live-spec gates remain |
| C03 | Main/manual/scheduled/release execution | Full exact-source validation; never reuse reduced PR output as release attestation |

## Deterministic and hosted validation

Run `scripts/dev doctor`, the full `scripts/dev check` and actual-index checks before
committing. The shared gate includes the unittest fixtures for index isolation, branch/
destination guards, custom hooks, missing prerequisites, specification resolution,
receipt safety and real package contracts. Those are deterministic controls, separate
from native model evidence.

For a feature PR, inspect both required Linux/macOS CI contexts for its current head.
Read logs for selected gates, ARM assertions, source-resolution provenance and archive
execution where applicable. Resolved official-source artifacts are available on the
run. Main/manual/scheduled/release validation remains full. A real docs/version PR
can demonstrate conservative reduction only with compatible exact-main baseline proof.
Never merge or create a release just to manufacture such proof.

## Single-client probes

From the selected checkout, with the intended client already authenticated:

```sh
python3 scripts/verify-agent.py --client codex --output /outside/source/codex.json
python3 scripts/verify-agent.py --client claude --output /outside/source/claude.json
python3 scripts/verify-agent.py --client antigravity --output /outside/source/antigravity.json
```

The runner exports tracked/nonignored source into an independent fixture, plants a
random instruction marker and creates text/shell/JSON fixtures. Its labelled fixture
observer wraps hook output without changing client trust or configuration. Raw client
streams remain transient; retained evidence is sanitized. Source base/dirty state,
per-file hashes and tree digest identify the tested bytes independently of a PASS label.
Runner-owned temporary repositories are removed after observation.

Codex/Claude test root valid edits and subdirectory defect edits, successful native
events, both path-specific diagnostics, exact non-mutated bytes, then native branch
denials when positive delivery is established. Antigravity requires actual edit-tool
observations; no native-hook parity is inferred because it has no adapter here.
Missing tools/authentication/review are BLOCKED. Missing expected diagnostics or
observed unauthorized changes fail. A failure must not be hidden by a later blocker.

For ordinary trusted Codex configuration, use a NEW clean disposable linked checkout:

```sh
./scripts/dev worktree chore/acceptance-codex-example /outside/source/codex-fixture
python3 scripts/verify-agent.py --client codex --codex-fixture /outside/source/codex-fixture --output /outside/source/codex.json
```

The linked fixture must share the selected source repository/HEAD and use the
`chore/acceptance-codex-` prefix. The runner refuses dirty inputs, source deletions
that an overlay cannot represent, and changed primary/source hook bindings. It
preserves the fixture/index and restores its original branch. It neither grants trust
nor force-checks out the primary main. Independent/main review can remain BLOCKED;
review definitions through the client's supported route before relying on them.

## Linked-worktree concurrency

```sh
python3 scripts/verify-agent-concurrency.py --client claude --output /outside/source/claude-linked.json
python3 scripts/verify-agent-concurrency.py --client antigravity --output /outside/source/antigravity-linked.json
```

Antigravity remains the default client. Both modes use separate runner-owned linked
worktrees, root/subdirectory launches, distinct markers/expected bytes and measured
client-process windows. Verify distinct unchanged branches/HEADs, exact allowed paths
including untracked files, source hashes and positive process overlap. Process overlap
includes tool time; it is not a measure of simultaneous inference.

Claude exposes only Read/Edit tools with empty strict MCP configuration and project
settings enabled. Each of the three Edit invocations must have its own ordered native
pre/post response and production receipt pair with matching tool identity. Both adapters
share the complete shell diff/lint and exact JSON diagnostic policy by fixture path.
Headers and prose alone fail. The optional production traces stay in private external
files; their metadata is correlated with native streams, never treated as proof alone.

Timeouts retain partial native observations after process-group termination/drain.
A prohibited call observed before timeout fails. Unavailable/incomplete runs with
fixtures still at original bytes remain BLOCKED; extra paths, changed HEADs and
corrupted/deleted bytes still fail. Cleanup removes only runner-owned temporary roots;
existing user fixtures require explicit cleanup authorization.

Use `--source /path/to/checkout` to export another production snapshot. Validator and
process helpers always come from the current harness checkout. Separate source and
harness-file hashes identify both; a baseline SHA alone cannot attest to dirty bytes.

## Native desktop and hosted scenarios

Run tests in the actual selected product/host. Establish execution mode and fixture
access before mutation; a local CLI is not a cloud/desktop substitute. Evaluate a
pre-planted instruction marker before opening instruction files. Later explicit reads
cannot establish automatic discovery retroactively.

Configure [optional invocation receipts](hook-scope.md#opt-in-invocation-receipts) in
the parent startup environment before launch. A child-shell export cannot change an
already running client. Capture actual tools, native responses and bytes, and retrieve
post-final lifecycle output when exposed. Missing telemetry remains unproven. Decline
external requests to commit deliberate defects; do not disable hooks to satisfy tests.

Copilot acceptance uses an actual GitHub-hosted agent task and separately submitted
PR review, not a Mac CLI or successful GitHub Actions run. Report access/entitlement
blockers without repeated unchanged requests or service activation. Cloud isolation,
network assumptions and Git enforcement need separate observations; a fresh clone
does not inherit another clone's hooks. Consult the [cloud setup runbook](development.md#claude-code-cloud-setup).

Completed issue-specific prompts, dated reports and raw receipt dumps belong in the
issue/CI history or an explicit external evidence location. Keep reusable scenarios
and the concise acceptance summary in the repository.
