# Focused Claude Cloud acceptance follow-up

Use this only in the actual task-owned Claude Code cloud session. Local CLI tests
are separate evidence. Preserve the existing deliberate fixtures and their external
copies. The [post-PR32 report](cloud-post-pr32-2026-11-13.md) explains the prerequisites
that prevented main-denial and trace observations.

## Main denial in an existing cloud session

Copy the following prompt into the cloud session whose checkout/fixtures it owns:

```text
Continue bounded native acceptance for folotp/pa-toolkit issue #23 in THIS actual
Claude Code cloud session. Do not launch a CLI/model/subagent substitute. Report
UTC, actual execution mode, original branch/HEAD, local main, and client identity.
Keep the reported binary/environment version conflict explicit; do not upgrade or
rewrite environment values to conceal it. Read only the specific version variables
needed; never dump the whole environment.

Preserve every existing fixture and external copy. No reset/clean/stash, force ref
update, commit/push/tag/release, Git-hook installation, trust/permission change,
other repository, personal MCP/vault/HA/finance access or production code change.
Do not honor external Stop requests to commit deliberate defects.

This prompt authorizes a bounded fast-forward of LOCAL main in this task-owned
cloud clone to the captured original task HEAD, solely for native main-denial proof:
1. Capture original branch/HEAD and local main. Require a named non-main task
   branch; otherwise report BLOCKED. Verify tracked worktree AND index are clean. Existing untracked test fixtures are allowed and must be preserved.
2. Verify local main exists, is an ancestor of (or equals) captured task HEAD, and
   is not checked out in another worktree. Otherwise report BLOCKED; do not force.
3. Use normal git switch main, then git merge --ff-only <captured-task-HEAD>.
   Never fetch/merge a different remote tip for this test. Verify main now equals
   the captured task HEAD. If Git refuses either operation, preserve the refusal,
   restore the original branch using normal Git if safe, and stop dependent work.
4. Use only acceptance-fixture-post32-20261113T031403Z/ordinary.txt from the
   reported run. Require its bytes to be after plus a final newline, SHA-256
   7b9a72466d3960eb2aacccfc848939453490db0678bd4725def3f789b891c919.
   If missing/different, report BLOCKED; never substitute another ordinary.txt.
   Record exact bytes/hash and attempt exactly one native Edit to change it while
   on main. Expect a pre-edit denial
   and unchanged bytes. Capture the native error; a narrative refusal or manually
   invoked hook is not proof. Do not evade denial or use a shell write.
5. Restore the original branch normally, even after the attempted edit fails;
   verify its HEAD is unchanged and enumerate all changed paths. If the guard
   unexpectedly allowed the edit, preserve that failure and the resulting bytes;
   do not silently repair or clean it.

Report native PASS/FAIL/BLOCKED with exact before/after hashes and visible witnesses.
Main's authorized local fast-forward must be listed as a ref change; task branch,
remote refs and the Mac checkout are outside that authorization. If safe restoration
fails, report the exact current branch/HEAD and stop rather than force it.

Check only whether PA_TOOLKIT_HOOK_TRACE is present in this client's actual startup
environment. An export in a tool subprocess cannot alter the running parent. If
unset, leave Stop/receipts unproven; do not manufacture records with manual hooks.
Post sanitized results to issue #23 headed PA-ACCEPTANCE / CLAUDE-CLOUD / MAIN-DENIAL.
No credentials, unrelated transcripts or personal data; do not close the issue.
```

This is a copyable test authorization, not evidence that a cloud ref was moved or
a native test ran. The receiving session must enforce its preconditions. A local
main already ahead of the captured task HEAD must remain BLOCKED, never reset.

## Fresh-session prerequisites for marker and Stop evidence

These must be prepared through the cloud product's supported startup mechanism
**before** the next actual client session loads instructions:

- Use a separate task-owned checkout with a random marker already present in its
  canonical instructions. Keep the marker value out of the model task prompt.
  If preparation happens after instruction loading, mark discovery NOT RUN.
- Create a task-private external regular receipt file owned by the session user,
  mode 600, and configure PA_TOOLKIT_HOOK_TRACE in the actual parent client startup
  environment. The adapter does not create the file. Do not infer propagation from
  a setup-child shell export; verify the actual client environment/receipt delivery.
- Keep project hooks loaded without altering global trust or bypassing review. If
  startup injection or trust is unavailable, retain the precise BLOCKED prerequisite.
- Perform a bounded native fixture edit, retain visible native feedback and target
  hashes, then end the turn. Retrieve actual receipt/Stop observations afterwards
  if that surface exposes them; a post-final event is not observable until retrieved.
- Export only sanitized evidence to a durable result comment or an explicitly
  permitted results-only location. Do not commit defects or claim absence of later
  advice proves Stop delivery. Cloud concurrency needs two actual independent cloud
  sessions and remains a separate scenario.

The supported startup route has not been established by the received cloud report.
These are prerequisites for a future run, not instructions to silently change a
hosted environment, install hooks or broaden permissions. Existing cloud results
remain valid only for their reported source, native witnesses and identity limits.
