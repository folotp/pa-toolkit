"""Conservative, declarative changed-file planning shared by repository adapters.

Only reviewed path classes can reduce PR checks. Full checks/releases do not use
prior local results. Missing bases, unknown paths and policy/engine changes fail
closed to the complete gate. Deletions/renames include both affected path names.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path, PurePosixPath
import subprocess

from .source import require


def validate_config(config):
    """Reject malformed plans and references rather than skipping an unknown gate."""
    require(
        isinstance(config, dict)
        and type(config.get("schema_version")) is int
        and config["schema_version"] == 1,
        "Development policy must be a schema_version 1 object",
    )
    require(
        set(config) == {"schema_version", "gates", "changes", "baseline"},
        "Unknown development policy keys",
    )
    baseline = config["baseline"]
    require(
        isinstance(baseline, dict)
        and set(baseline) == {"repository", "workflow", "branch", "policy_paths"},
        "Invalid baseline configuration",
    )
    require(
        all(
            isinstance(baseline[k], str) and baseline[k].strip()
            for k in ("repository", "workflow", "branch")
        ),
        "Invalid baseline identity",
    )
    require(
        isinstance(baseline["policy_paths"], list)
        and baseline["policy_paths"]
        and all(isinstance(x, str) and x for x in baseline["policy_paths"]),
        "Invalid baseline policy paths",
    )
    gates = config["gates"]
    require(isinstance(gates, dict) and gates, "Development gates must be a nonempty object")
    for name, rule in gates.items():
        require(isinstance(rule, dict) and set(rule) == {"argv", "always"}, f"Invalid gate: {name}")
        require(
            type(rule["always"]) is bool
            and isinstance(rule["argv"], list)
            and rule["argv"]
            and all(isinstance(x, str) and x.strip() for x in rule["argv"]),
            f"Invalid gate argv: {name}",
        )
    rules = config["changes"]
    require(isinstance(rules, list) and rules, "Development change classes must be nonempty")
    for rule in rules:
        require(
            isinstance(rule, dict) and set(rule) == {"name", "patterns", "gates", "full"},
            "Invalid change class",
        )
        require(
            isinstance(rule["name"], str) and rule["name"].strip() and type(rule["full"]) is bool,
            "Invalid change class name/full",
        )
        require(
            isinstance(rule["patterns"], list)
            and rule["patterns"]
            and all(isinstance(x, str) and x for x in rule["patterns"]),
            "Invalid change patterns",
        )
        require(
            isinstance(rule["gates"], list)
            and all(isinstance(x, str) and x in gates for x in rule["gates"]),
            "Change class references unknown gate",
        )


def classify(config, paths=None, reason=None):
    """Return an ordered gate plan with explanations; never infer from PR titles.

    A path can match several classes; their union determines affected gates. No
    extension-based blanket exemption exists: unknown Markdown is a full fallback.
    `paths=None` means unavailable comparison, not a trusted empty diff.
    """
    validate_config(config)
    gates = config["gates"]
    full_reason = reason or ("comparison unavailable" if paths is None else None)
    selected = {name for name, rule in gates.items() if rule["always"]}
    classes = set()
    for name in paths or []:
        require(isinstance(name, str) and name, "Changed paths must be nonempty strings")
        path = PurePosixPath(name)
        require(not path.is_absolute() and ".." not in path.parts, f"Unsafe changed path: {name}")
        matches = [
            rule
            for rule in config["changes"]
            if any(fnmatch.fnmatchcase(name, p) for p in rule["patterns"])
        ]
        if not matches:
            full_reason = f"unknown path: {name}"
        for rule in matches:
            classes.add(rule["name"])
            selected.update(rule["gates"])
            if rule["full"]:
                full_reason = f"full-impact path: {name}"
    if full_reason:
        selected = set(gates)
    return {
        "full": bool(full_reason),
        "reason": full_reason or "reviewed changed-file classes",
        "classes": sorted(classes),
        "paths": sorted(paths or []),
        "run": [name for name in gates if name in selected],
        "skip": [name for name in gates if name not in selected],
    }


def changed_paths(root, base, head="HEAD"):
    """Read a complete Git diff; incomplete history yields full-check fallback.

    --no-renames reports a rename as delete+add, preserving both impact paths. CI
    supplies the PR merge base; the index exporter supplies a real isolated index.
    Never use GitHub's truncated changed-files API to decide what can be skipped.
    """
    if not base:
        return None
    try:
        subprocess.run(
            ["git", "cat-file", "-e", base + "^{commit}"],
            cwd=root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        output = subprocess.check_output(
            ["git", "diff", "--no-renames", "--name-only", "-z", base, head, "--"], cwd=root
        )
        return [p.decode("utf-8") for p in output.split(b"\0") if p]
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        return None


def execute(root, config, plan):
    """Run the declared commands in order, showing every run/skip and propagating failure."""
    validate_config(config)
    require(
        set(plan["run"]) | set(plan["skip"]) == set(config["gates"])
        and set(plan["run"]).isdisjoint(plan["skip"]),
        "Plan does not cover every gate exactly once",
    )
    for name, rule in config["gates"].items():
        if name not in plan["run"]:
            print(f"SKIP {name}: unchanged inputs ({plan['reason']})", flush=True)
            continue
        print(f"RUN {name}: {plan['reason']}", flush=True)
        subprocess.run(rule["argv"], cwd=Path(root), check=True)


def trusted_github_base(root, base, repository, workflow, policy_paths, branch="main", fetch=None):
    """Require a successful full protected-main push run and unchanged planner policy.

    This is only permission to omit unaffected PR gates, not a release receipt.
    Unavailable history/API, policy drift, another branch/event or failed/in-progress
    runs cause full validation. The caller keeps main pushes/releases unconditionally
    full. Never accept a client-supplied success flag or a local test receipt.
    """
    import json
    import os
    import re
    import urllib.parse
    import urllib.request

    if (
        not base
        or not re.fullmatch(r"[0-9a-f]{40}", base)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
    ):
        return False
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, "HEAD"],
            cwd=root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Require the baseline to contain each input, including directory trees.
        # Compare staged and unstaged bytes too; CI additionally requires a clean tree.
        for name in policy_paths:
            subprocess.run(
                ["git", "cat-file", "-e", f"{base}:{name}"],
                cwd=root,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        subprocess.run(
            ["git", "diff", "--quiet", base, "--", *policy_paths],
            cwd=root,
            check=True,
        )
        query = urllib.parse.urlencode(
            {"event": "push", "branch": branch, "head_sha": base, "per_page": 100}
        )
        url = f"https://api.github.com/repos/{repository}/actions/runs?{query}"
        if fetch is None:
            headers = {"Accept": "application/vnd.github+json", "User-Agent": "pa-devtools/0.1"}
            if os.environ.get("GH_TOKEN"):
                headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=15
            ) as response:
                payload = json.load(response)
        else:
            payload = fetch(url)
        return any(
            run.get("head_sha") == base
            and run.get("head_branch") == branch
            and run.get("event") == "push"
            and run.get("path") == workflow
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            for run in payload["workflow_runs"]
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        subprocess.CalledProcessError,
    ):
        return False
