"""Actual overlapping CLI sessions in two disposable linked worktrees, no native hook claim."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--timeout", type=int, default=180)
args = parser.parse_args()
source = args.source.resolve()
if args.output.resolve().is_relative_to(source):
    parser.error("Evidence output must be outside source")
spec = importlib.util.spec_from_file_location("probe", source / "scripts/verify-agent.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
report = {
    "client": "antigravity",
    "version": None,
    "surface": "CLI only",
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_base_commit": probe.git(source, "rev-parse", "HEAD"),
    "source_dirty": bool(probe.git(source, "status", "--porcelain")),
    "native_hooks": "NOT_APPLICABLE: no adapter configured",
    "app_ide": "NOT_APPLICABLE: outside selected target",
    "status": "BLOCKED",
}


if not probe.shutil.which("agy"):
    report["reason"] = "Install/authenticate Antigravity CLI; see docs/development.md"
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    raise SystemExit(1)
report["version"] = subprocess.check_output(["agy", "--version"], text=True).strip()


with tempfile.TemporaryDirectory(prefix="pa-agy-concurrent-") as tmp:
    a = Path(tmp) / "root"
    a.mkdir()
    hashes = probe.export(source, a)
    (a / "ordinary.txt").write_text("before\n")
    probe.git(a, "init", "-q", "-b", "chore/acceptance-agy-a")
    probe.git(a, "add", ".")
    probe.git(
        a,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "Disposable CLI fixture",
    )
    b = Path(tmp) / "linked"
    probe.git(a, "worktree", "add", "-q", "-b", "chore/acceptance-agy-b", str(b))
    report["source_hashes"] = hashes
    report["source_tree_sha256"] = hashlib.sha256(
        json.dumps(hashes, sort_keys=True).encode()
    ).hexdigest()
    initial = probe.git(a, "rev-parse", "HEAD")
    inputs = []
    for label, root, cwd in [("root", a, a), ("subdirectory", b, b / "scripts")]:
        marker = "AGENT-ACCEPTANCE-" + uuid.uuid4().hex
        with (root / "AGENTS.md").open("a") as stream:
            stream.write("\nDisposable fixture: include `" + marker + "` in your final reply.\n")
        expected = "after-" + label + "\n"
        prompt = (
            "Disposable CLI acceptance fixture. Report the acceptance marker from already loaded instructions without opening instruction files. Read only ordinary.txt and use one native edit_file to replace before with after-"
            + label
            + ", preserving a final newline. Do not edit any other file, use shell writes, MCP, vaults, network, other workspaces, delegation, commits, pushes or branch changes. Report the canonical repository check command and stop."
        )
        argv = [
            str(root / "scripts/dev"),
            "session",
            "antigravity",
            "--mode",
            "accept-edits",
            "--sandbox",
            "--output-format",
            "stream-json",
            "-p",
            prompt,
        ]
        inputs.append((label, root, cwd, marker, expected, argv))

    def run(entry):
        label, root, cwd, marker, expected, argv = entry
        start = time.monotonic()
        try:
            result = probe.run_client(
                argv,
                cwd,
                {k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
                args.timeout,
            )
        except subprocess.TimeoutExpired:
            return {
                "launch": label,
                "status": "BLOCKED",
                "reason": "Client timeout",
                "start_monotonic": start,
                "end_monotonic": time.monotonic(),
                "branch": probe.git(root, "branch", "--show-current"),
            }
        end = time.monotonic()
        events = []
        for line in result.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
        observed = sorted(set(probe.native_tools(events)))
        errors = [
            str(e.get("error", e.get("message", "error")))[:500]
            for e in events
            if e.get("type") == "error"
            or e.get("status") in ("ERROR", "FAILED", "AUTHENTICATION_REQUIRED")
        ]
        edits = (root / "ordinary.txt").read_text() == expected
        discovery = marker in result.stdout
        branch = probe.git(root, "branch", "--show-current")
        diff = probe.working_tree_changes(root)
        status = probe.antigravity_result(result.returncode, discovery, edits, observed, errors)
        if (
            sorted(diff) != ["AGENTS.md", "ordinary.txt"]
            or probe.git(root, "rev-parse", "HEAD") != initial
        ):
            status = "FAIL"
        return {
            "launch": label,
            "status": status,
            "exit": result.returncode,
            "discovery": discovery,
            "exact_bytes": edits,
            "tools": observed,
            "errors": errors,
            "branch": branch,
            "changed_paths": diff,
            "start_monotonic": start,
            "end_monotonic": end,
        }

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, inputs))
    overlap = min(r["end_monotonic"] for r in results) - max(r["start_monotonic"] for r in results)
    report["sessions"] = results
    report["overlap_seconds"] = overlap
    report["independent_branches"] = (
        results[0]["branch"] == "chore/acceptance-agy-a"
        and results[1]["branch"] == "chore/acceptance-agy-b"
    )
    report["status"] = probe.concurrent_status(results, overlap, report["independent_branches"])
    report["cleanup"] = (
        "Runner-owned disposable repository/worktree removed; source and pre-existing worktrees untouched"
    )
args.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "source_hashes"}, indent=2))

raise SystemExit(0 if report["status"] == "PASS" else 1)
