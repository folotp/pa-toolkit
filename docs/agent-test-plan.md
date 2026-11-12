# Reusable multi-agent development acceptance plan

## Scope and evidence rules

Parameterize this plan with repository, source commit/dirty source hashes, client
product/version/surface, source worktree, explicit external evidence directory,
required commands and authoritative CI contexts. Apply it separately to pa-toolkit,
pa-marketplace, organon-plugin and ha-config; retain each repository's domain gates.
CI is a validation surface, not an AI agent. Do not require model credentials in CI.

Use PASS / FAIL / BLOCKED / NOT RUN / NOT APPLICABLE. Record expected and observed
behavior, commands, UTC date, versions, fixture mode, actual bytes/event witnesses,
cleanup and remaining limitations. A model's narrative, successful config parse or
manual subprocess call does not prove native event delivery. A trusted/pinned older
result does not certify later source. BLOCKED is non-success, not a skipped pass.

All fixtures are independent disposable repositories or separately named worktrees
outside any vault mount. Source branches/indexes, user/global trust/settings, related
repositories, marketplace pins and live systems remain unchanged. No hooks, sandbox,
branch protection or permissions are bypassed. Do not run a live bumper, merge,
release, deploy or access a personal vault to prove developer tooling works.

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

G/E/P fixtures already live in the repository's unittest suite; run
`uv run --locked python -m unittest discover -s tests -v` and the full/index gates.
Native tests complement those fixtures. They do not replace them or generalize to
unsupported shell/MCP/cloud paths.

## Reusable real-client runner

From the selected checkout, with the desired client already authenticated:

```sh
python3 scripts/verify-agent.py --client codex --output /outside/source/codex.json
python3 scripts/verify-agent.py --client claude --output /outside/source/claude.json
```

The stdlib runner exports tracked/nonignored current source into an independent
repository, adds random instruction marker and shell/JSON fixtures, then starts the
real client through `scripts/dev session` from a subdirectory. It wraps `hook()`
only inside the disposable fixture to retain bounded actual event output. It never
adds invocation-local trust overrides. The evidence distinguishes the observer from
unchanged production source and records source hashes. Raw streams remain in memory;
only sanitized selected evidence is saved. Temporary repositories are removed.

The positive run covers discovery, native edits, feedback and start/stop. Detached
native denial runs only after native delivery is witnessed. Hook trust/discovery
blockers are reported without a bypass or persistent trust change. Exit 0 requires
all implemented native scenarios; partial/BLOCKED/FAIL returns nonzero. Model calls
are optional live acceptance, not part of the deterministic unittest/CI gate.

Copilot/Antigravity manual execution uses the same fixture operations and statuses:
open a separately selected disposable checkout in the exact CLI/IDE/cloud product,
verify the instruction reference and marker, perform A02-A04, record supported native
hooks or explicit Git/CI fallback, then run applicable G/E/S/P scenarios. Do not claim
Claude/Codex JSON hook configuration applies to either product. Record unavailable
clients/auth and IDE-only controls as blockers. Do not silently install clients.

## Hosted CI procedure

Push the implementation branch normally, open a review PR, and record the head SHA,
workflow run, both required statuses and ARM assertion. Read logs to verify the
selected gates and download `official-specifications-*` artifacts for resolved
sources/results. Repeat only for changed source or a failed/unresolved check.
Use a genuine subsequent docs/version PR to observe reduction once its base has
successful compatible main-push CI; never merge or manufacture a release to test it.
