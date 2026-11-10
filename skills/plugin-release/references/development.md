# Release infrastructure development

The shared release runbook is `runbook.md`; Claude's executor is an adapter. The portable driver is `../scripts/release.py`. Python 3.9+, Git, jq, zip and tar are required; no new Python packages are needed. Tests run with:

```sh
python3 -m unittest discover -s tests -v
```

CI exercises Linux and macOS. The low-level generic packager is unchanged in this change; its existing shfmt differences are outside this work. ShellCheck passes. The driver snapshots tracked HEAD for repositories without an extension; untracked and ignored artifacts cannot leak. An explicit extension can supply stricter runtime selection and mandatory repository checks.

## Branch guards and protected main

Install local guards from a stable selected checkout:

```sh
python3 /path/to/pa-toolkit/skills/plugin-release/scripts/branch-guard.py install
```

Run that command in the target repository. It respects Git's hook path and linked worktrees, preserves unmanaged hooks, rejects main/detached commits and direct pushes whose destination is main. The generated launcher points to the selected driver; retain that checkout or reinstall after moving it. Organon already owns a stronger staged-snapshot pre-commit check: preserve it rather than replacing it.

Require PRs for main, enforce for admins, disallow force pushes and deletion. Require the two Release checks once CI exists. Releases only tag exact commits already merged to remote main. Marketplace automation must open/update a PR and validate it; do not enable PR protection on a direct-push bot without adapting that workflow first. GitHub Actions must be allowed to create pull requests in the repository settings.

Changes to this source checkout do not update installed plugin copies. Select a checkout explicitly during development; distributing a version is a separate authorized release.
