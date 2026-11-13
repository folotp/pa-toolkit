"""Overlapping real CLI sessions in runner-owned linked worktrees.

Antigravity keeps its CLI edit-only contract. Claude additionally correlates native
Edit calls and hook responses with unmodified production invocation receipts. No
model credentials are needed by deterministic tests; stubs are labelled as such.
"""

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


# --source chooses exported production bytes, never an older validator implementation.
# Both harness entry points share this checkout's authoritative evidence policy.
HELPER = Path(__file__).with_name("verify-agent.py")
SPEC = importlib.util.spec_from_file_location("probe", HELPER)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def timeout_stream(value):
    """Support Python's byte timeout output as well as the shared text contract."""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")


def structured_events(stream):
    """Ignore non-JSON progress lines; never treat narrative text as a tool event."""
    events = []
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def claude_witnesses(events, root):
    """Retain only native fixture tool calls and bounded system hook responses.

    Arbitrary assistant prose is excluded. Discovery must not rely on explicit
    instruction-file reads; unexpected native tools/paths are observed violations.
    Full raw streams remain in memory and are discarded after inspection.
    """
    calls, responses, shapes = [], [], []
    for event in events:
        if event.get("type") == "assistant":
            message = event.get("message", {})
            for block in message.get("content", []) if isinstance(message, dict) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    inputs = block.get("input", {})
                    name = inputs.get("file_path") if isinstance(inputs, dict) else None
                    path = None
                    if isinstance(name, str):
                        resolved = (root / name).resolve()
                        path = (
                            resolved.relative_to(root.resolve()).as_posix()
                            if resolved.is_relative_to(root.resolve())
                            else "<outside-fixture>"
                        )
                    calls.append({"tool": block.get("name"), "path": path})
        if event.get("type") == "system" and "hook" in str(event.get("subtype", "")):
            shape = {"subtype": event.get("subtype"), "keys": sorted(event)}
            if shape not in shapes:
                shapes.append(shape)
            if event.get("subtype") == "hook_response":
                response = {"exit_code": event.get("exit_code")}
                for key in ("hook_event", "hook_name", "stdout", "stderr", "outcome"):
                    text = str(event.get(key, ""))
                    for prefix in sorted({str(root), str(root.resolve())}, key=len, reverse=True):
                        text = text.replace(prefix, "<fixture>")
                    response[key] = text[:4000]
                responses.append(response)
    return calls, responses, shapes


def claude_outcome(exit_code, discovery, edits, calls, responses, receipts, errors):
    """Validate exact edits and actual witnesses; absence of telemetry is BLOCKED.

    An observed unauthorized call, byte defect, failed hook or missing diagnostic
    is FAIL. Client failures are BLOCKED unless an observed violation takes priority.
    A receipt alone can be manually manufactured and is never native delivery proof.
    """
    targets = {"ordinary.txt", "smoke.sh", "smoke.json"}
    if any(c["tool"] not in {"Read", "Edit"} or c["path"] not in targets for c in calls):
        return "FAIL"
    if any(r.get("exit") != 0 or r.get("outcome") != "completed" for r in receipts):
        return "FAIL"
    if any(
        r.get("exit_code") not in (None, 0) or r.get("outcome") not in ("", "success")
        for r in responses
    ):
        return "FAIL"
    edit_calls = [call for call in calls if call["tool"] == "Edit"]
    # A set loses duplicate invocations. Every intended target must be edited once,
    # with exactly one pre/post pair; an extra unwitnessed call is an observed FAIL.
    if len(edit_calls) > len(targets) or len({c["path"] for c in edit_calls}) != len(edit_calls):
        return "FAIL"
    if any(r.get("event") in {"edit", "feedback"} and r.get("tool") != "Edit" for r in receipts):
        return "FAIL"
    if any(r.get("event") in {"start", "stop"} and r.get("tool") is not None for r in receipts):
        return "FAIL"
    if any(
        r.get("hook_event") in {"PreToolUse", "PostToolUse"}
        and r.get("hook_name", "").partition(":")[2] != "Edit"
        for r in responses
    ):
        return "FAIL"
    if exit_code or errors:
        return "BLOCKED"
    if not discovery or not edits:
        return "FAIL"
    if len(edit_calls) != len(targets):
        return "BLOCKED"
    expected_receipts = [("start", None)]
    expected_responses = ["SessionStart"]
    for call in edit_calls:
        expected_receipts.extend([("edit", call["tool"]), ("feedback", call["tool"])])
        expected_responses.extend(["PreToolUse", "PostToolUse"])
    expected_receipts.append(("stop", None))
    expected_responses.append("Stop")
    if len(receipts) < len(expected_receipts) or len(responses) < len(expected_responses):
        return "BLOCKED"
    if [(r.get("event"), r.get("tool")) for r in receipts] != expected_receipts:
        return "FAIL"
    if [r.get("hook_event") for r in responses] != expected_responses:
        return "FAIL"
    if any(r.get("exit_code") != 0 or r.get("outcome") != "success" for r in responses):
        return "BLOCKED"
    post = [r for r in responses if r["hook_event"] == "PostToolUse"]
    feedback = [
        {"paths": [call["path"]], "stdout": response["stdout"]}
        for call, response in zip(edit_calls, post)
    ]
    shell, invalid_json = probe.diagnostic_coverage(feedback)
    if not shell or not invalid_json:
        return "FAIL"
    return "PASS"


def fixture_bytes_outcome(before, expected, actual):
    """Distinguish unfinished work from observed corruption on client failure.

    A timeout/auth failure can leave a fixture at its original bytes. Any third
    value or deletion is an observed violation and must not be hidden as BLOCKED.
    """
    exact = actual == expected
    invalid = any(
        actual.get(name) not in (original, expected[name]) for name, original in before.items()
    )
    return exact, invalid


def session_violation(changed, allowed, before_head, after_head, incomplete_run):
    """Observed extra paths/HEAD changes fail even on timeout or client error.

    Missing edits after an incomplete run are unproven, not a mutation failure.
    Branch identity is independently checked after both sessions finish.
    """
    return (
        before_head != after_head
        or bool(set(changed) - set(allowed))
        or (not incomplete_run and set(changed) != set(allowed))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--client", choices=("antigravity", "claude"), default="antigravity")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    source = args.source.resolve()
    if args.output.resolve().is_relative_to(source):
        parser.error("Evidence output must be outside source")
    client = args.client
    executable = "agy" if client == "antigravity" else "claude"
    report = {
        "client": client,
        "version": None,
        "surface": "local CLI print" if client == "claude" else "CLI only",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_base_commit": probe.git(source, "rev-parse", "HEAD"),
        "source_dirty": bool(probe.git(source, "status", "--porcelain")),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "harness_hashes": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__), HELPER)
        },
        "fixture_observer": False,
        "native_hooks": "production receipts plus native client stream"
        if client == "claude"
        else "NOT_APPLICABLE: no adapter configured",
        "app_ide": "NOT_RUN: separate selected surface"
        if client == "claude"
        else "NOT_APPLICABLE: outside selected target",
        "status": "BLOCKED",
    }
    blockers = probe.prerequisites() if client == "claude" else []
    if not probe.shutil.which(executable):
        blockers.append(f"Install/authenticate {executable}; see docs/development.md")
    if blockers:
        report["reason"] = "; ".join(blockers)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        return 1
    report["version"] = subprocess.check_output([executable, "--version"], text=True).strip()
    original_status = probe.git(source, "status", "--porcelain", "--untracked-files=all")
    with tempfile.TemporaryDirectory(prefix="pa-cli-concurrent-") as tmp:
        temporary = Path(tmp)
        a = temporary / "root"
        a.mkdir()
        hashes = probe.export(source, a)
        before = {"ordinary.txt": "before\n"}
        if client == "claude":
            before.update(
                {
                    "smoke.sh": "#!/usr/bin/env bash\necho before\n",
                    "smoke.json": '{"before":true}\n',
                }
            )
        for name, content in before.items():
            (a / name).write_text(content)
        prefix = "chore/acceptance-" + ("agy" if client == "antigravity" else "claude")
        probe.git(a, "init", "-q", "-b", prefix + "-a")
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
        b = temporary / "linked"
        probe.git(a, "worktree", "add", "-q", "-b", prefix + "-b", str(b))
        report["source_hashes"] = hashes
        report["source_tree_sha256"] = hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode()
        ).hexdigest()
        initial = probe.git(a, "rev-parse", "HEAD")
        inputs = []
        for label, root, cwd in [("root", a, a), ("subdirectory", b, b / "scripts")]:
            marker = "AGENT-ACCEPTANCE-" + uuid.uuid4().hex
            with (root / "AGENTS.md").open("a") as stream:
                stream.write(
                    "\nDisposable fixture: include `" + marker + "` in your final reply.\n"
                )
            expected = "after-" + label + "\n"
            trace = temporary / (label + "-events.jsonl")
            trace.touch(mode=0o600)
            prompt = (
                "Disposable CLI acceptance fixture. Report the acceptance marker from already loaded instructions without opening instruction files. Read only ordinary.txt and use one native "
                + ("Edit" if client == "claude" else "edit_file")
                + " to replace before with after-"
                + label
                + ", preserving a final newline. "
            )
            if client == "claude":
                prompt += 'Also read smoke.sh and smoke.json and use native Edit sequentially to replace echo before with if true;then echo after;fi and {"before":true} with {"invalid":}. Preserve final newlines and leave these intentional defects intact. '
            prompt += "Do not edit any other file, use shell writes, MCP, vaults, network, other workspaces, delegation, commits, pushes or branch changes. Report the canonical repository check command and received native feedback, then stop."
            if client == "claude":
                argv = [
                    str(root / "scripts/dev"),
                    "session",
                    client,
                    "-p",
                    "--setting-sources",
                    "project",
                    "--strict-mcp-config",
                    "--mcp-config",
                    '{"mcpServers":{}}',
                    "--tools",
                    "Read,Edit",
                    "--allowedTools",
                    "Read,Edit",
                    "--no-session-persistence",
                    "--output-format",
                    "stream-json",
                    "--include-hook-events",
                    "--verbose",
                    prompt,
                ]
            else:
                argv = [
                    str(root / "scripts/dev"),
                    "session",
                    client,
                    "--mode",
                    "accept-edits",
                    "--sandbox",
                    "--output-format",
                    "stream-json",
                    "-p",
                    prompt,
                ]
            inputs.append((label, root, cwd, marker, expected, argv, trace))

        def run(entry):
            label, root, cwd, marker, expected, argv, trace = entry
            env = {
                k: v
                for k, v in os.environ.items()
                if not k.startswith("GIT_")
                and k not in {"PA_TOOLKIT_HOOK_TRACE", "PA_TOOLKIT_TEST_EVENTS"}
            }
            if client == "claude":
                env["PA_TOOLKIT_HOOK_TRACE"] = str(trace)
            start = time.monotonic()
            timeout = False
            try:
                result = probe.run_client(argv, cwd, env, args.timeout)
            except subprocess.TimeoutExpired as error:
                timeout = True
                result = subprocess.CompletedProcess(
                    argv, 1, timeout_stream(error.stdout), timeout_stream(error.stderr)
                )
            end = time.monotonic()
            events = structured_events(result.stdout)
            observed = sorted(set(probe.native_tools(events)))
            errors = [
                str(e.get("error", e.get("message", "error")))[:500]
                for e in events
                if e.get("type") == "error"
                or e.get("status") in ("ERROR", "FAILED", "AUTHENTICATION_REQUIRED")
                or e.get("is_error") is True
            ]
            expected_contents = {"ordinary.txt": expected}
            if client == "claude":
                expected_contents.update(
                    {
                        "smoke.sh": "#!/usr/bin/env bash\nif true;then echo after;fi\n",
                        "smoke.json": '{"invalid":}\n',
                    }
                )
            actual = {
                name: (root / name).read_text() if (root / name).is_file() else None
                for name in before
            }
            edits, invalid_bytes = fixture_bytes_outcome(before, expected_contents, actual)
            discovery = marker in result.stdout
            calls, responses, shapes = (
                claude_witnesses(events, root) if client == "claude" else ([], [], [])
            )
            receipts = structured_events(trace.read_text())
            status = (
                claude_outcome(
                    result.returncode, discovery, edits, calls, responses, receipts, errors
                )
                if client == "claude"
                else probe.antigravity_result(result.returncode, discovery, edits, observed, errors)
            )
            diff = probe.working_tree_changes(root)
            allowed_paths = ["AGENTS.md", "ordinary.txt"] + (
                ["smoke.json", "smoke.sh"] if client == "claude" else []
            )
            branch = probe.git(root, "branch", "--show-current")
            incomplete_run = timeout or result.returncode != 0 or bool(errors)
            if invalid_bytes or session_violation(
                diff, allowed_paths, initial, probe.git(root, "rev-parse", "HEAD"), incomplete_run
            ):
                status = "FAIL"
            return {
                "launch": label,
                "status": status,
                "exit": result.returncode,
                "timeout": timeout,
                "incomplete_client_run": incomplete_run,
                "discovery": discovery,
                "exact_bytes": edits,
                "unexpected_fixture_bytes": invalid_bytes,
                "tools": observed,
                "errors": errors,
                "branch": branch,
                "changed_paths": diff,
                "start_monotonic": start,
                "end_monotonic": end,
                "native_calls": calls,
                "hook_responses": responses,
                "hook_event_shapes": shapes,
                "invocation_receipts": receipts,
                "fixture_hashes": {
                    name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                    if (root / name).is_file()
                    else None
                    for name in allowed_paths
                },
            }

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, inputs))
        overlap = min(r["end_monotonic"] for r in results) - max(
            r["start_monotonic"] for r in results
        )
        report["sessions"] = results
        report["overlap_seconds"] = overlap
        report["independent_branches"] = (
            results[0]["branch"] == prefix + "-a" and results[1]["branch"] == prefix + "-b"
        )
        report["source_unchanged"] = (
            probe.git(source, "rev-parse", "HEAD") == report["source_base_commit"]
            and probe.git(source, "status", "--porcelain", "--untracked-files=all")
            == original_status
            and all(
                (source / name).is_file()
                and hashlib.sha256((source / name).read_bytes()).hexdigest() == digest
                for name, digest in hashes.items()
            )
        )
        report["status"] = probe.concurrent_status(
            results, overlap, report["independent_branches"] and report["source_unchanged"]
        )
        report["cleanup"] = (
            "Runner-owned disposable repository/worktree removed; source and pre-existing worktrees untouched"
        )
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "source_hashes"}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
