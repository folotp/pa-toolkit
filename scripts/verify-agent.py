"""Reusable real-client acceptance probe in an independent disposable repository.

Exports selected source bytes (including current WIP) without modifying its index.
Only deterministic fixture outcomes and bounded native-hook observations are retained;
raw client streams are temporary. No trust, sandbox or Git-hook bypass is permitted.
A fixture-only observer wraps the unchanged hook function, not client configuration.
An absent observer record means native delivery was not proven, regardless of what
an agent says. Missing clients/authentication or untrusted hooks are explicit blockers.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import uuid


OBSERVER = """
# Disposable acceptance observer, not installed production policy.
_original_hook = hook
def hook(event):
    import contextlib, io, os
    raw = sys.stdin.read()
    payload = json.loads(raw)
    output, errors = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            sys.stdin = io.StringIO(raw)
            _original_hook(event)
    except (ValueError, OSError, SyntaxError, subprocess.CalledProcessError) as error:
        code = 2
        errors.write(str(error))
        raise
    finally:
        paths = []
        if event in ("edit", "feedback"):
            try:
                paths = [path.name for path in hook_paths(payload)]
            except (ValueError, OSError):
                pass
        item = {"event":event,"tool":payload.get("tool_name"),"exit":code,"paths":paths,
                "stdout":output.getvalue().replace(str(ROOT),"<fixture>")[:4000],
                "stderr":errors.getvalue().replace(str(ROOT),"<fixture>")[:1000]}
        with open(os.environ["PA_TOOLKIT_TEST_EVENTS"],"a") as stream:
            stream.write(json.dumps(item)+"\\n")
        print(output.getvalue(),end="")
        print(errors.getvalue(),end="",file=sys.stderr)
"""


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def export(source, root):
    """Copy tracked/nonignored sources, excluding environments and user-local settings."""
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=source
    )
    digests = {}
    for name in names.decode().split("\0"):
        if not name:
            continue
        path = source / name
        if not path.is_file() or path.is_symlink():
            continue
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def run_client(argv, cwd, env, timeout):
    """Bound a whole client process group, including tool children, on timeout."""
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        raise
    return subprocess.CompletedProcess(argv, process.returncode, out, err)


@contextmanager
def fixture(source, client, linked=None):
    """Export into a temp repo or an explicitly selected clean disposable worktree.

    Linked Codex mode uses ordinary existing configuration and never grants trust.
    Preserve that fixture, its index and original branch. Only runner-owned temporary
    repositories are automatically removed. Exported WIP is identified by hashes.
    """
    if linked is None:
        with tempfile.TemporaryDirectory(prefix="pa-agent-acceptance-") as directory:
            root = Path(directory)
            yield root, export(source, root)
        return
    linked = linked.resolve()
    if client != "codex" or linked == source.resolve():
        raise ValueError("Linked fixture requires Codex and a separate disposable checkout")
    branch = git(linked, "branch", "--show-current")
    if not branch.startswith("chore/acceptance-codex-"):
        raise ValueError("Fixture branch must start with chore/acceptance-codex-")
    if git(linked, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Linked fixture must be clean, including untracked files")
    common = ("rev-parse", "--path-format=absolute", "--git-common-dir")
    if git(linked, *common) != git(source, *common):
        raise ValueError("Linked fixture must belong to the selected source repository")
    if git(linked, "rev-parse", "HEAD") != git(source, "rev-parse", "HEAD"):
        raise ValueError("Linked fixture must start at the selected source HEAD")
    if git(source, "ls-files", "--deleted"):
        raise ValueError(
            "Use an independent fixture for source deletions; linked export overlays HEAD"
        )
    # This installed Codex can select primary-checkout definitions for a linked cwd.
    # Never certify changed bindings by accidentally running an older trusted copy.
    primary = Path(git(source, "worktree", "list", "--porcelain").splitlines()[0][9:])
    bindings = Path(".codex/hooks.json")
    if (source / bindings).read_bytes() != (primary / bindings).read_bytes():
        raise ValueError("Changed hook definitions require isolated project/hook review")
    try:
        yield linked, export(source, linked)
    finally:
        if git(linked, "branch", "--show-current") != branch:
            git(linked, "switch", branch)


def provenance(source, hashes):
    """Identify exported bytes, including dirty source, independently of model results."""
    return {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_base_commit": git(source, "rev-parse", "HEAD"),
        "source_dirty": bool(git(source, "status", "--porcelain")),
        "source_tree_sha256": hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode()
        ).hexdigest(),
        "source_hashes": hashes,
    }


def startup_signals(stderr):
    """Retain recognized startup categories even on exit zero, never raw user config."""
    patterns = {
        "project_layer_disabled": r"[Pp]roject config.toml files are disabled|To load project-local config",
        "hook_review_required": r"[Hh]ooks?.{0,80}(?:review|untrusted)|/hooks",
    }
    return [name for name, pattern in patterns.items() if re.search(pattern, stderr)]


def prerequisites():
    """Return setup blockers before spending a model call on unavailable diagnostics."""
    failures = []
    for name, flag in (
        ("git", "--version"),
        ("python3", "--version"),
        ("shfmt", "--version"),
        ("shellcheck", "--version"),
    ):
        executable = shutil.which(name)
        if not executable:
            failures.append(f"Install {name}; see docs/development.md")
            continue
        try:
            result = subprocess.run([executable, flag], capture_output=True, text=True, timeout=10)
            if result.returncode:
                failures.append(f"Repair {name}: version probe exited {result.returncode}")
        except (OSError, subprocess.TimeoutExpired) as error:
            failures.append(f"Repair {name}: {error}")
    return failures


def positive_result(events, edits, discovery, client_exit, blockers=()):
    """Require successful events and path-specific detection of BOTH deliberate defects.

    Event names alone never certify diagnostics. Missing prerequisites are BLOCKED;
    failed positive hooks, missing path coverage/diagnostics or changed fixture bytes
    are FAIL. Missing native delivery remains BLOCKED without claiming native parity.
    """
    observed = {event["event"] for event in events}
    delivery = {"start", "edit", "feedback", "stop"} <= observed
    if blockers:
        return "BLOCKED", delivery, "BLOCKED: " + "; ".join(blockers)
    unavailable = any(
        re.search(
            r"No such file|not found|exit 127",
            event.get("stdout", "") + event.get("stderr", ""),
            re.I,
        )
        for event in events
    )
    if unavailable:
        return (
            "BLOCKED",
            delivery,
            "BLOCKED: diagnostic prerequisite unavailable; run scripts/dev doctor",
        )
    if any(event.get("exit") != 0 for event in events):
        return "FAIL", delivery, "FAIL: positive-run hook exited nonzero"
    if client_exit:
        return "BLOCKED", delivery, "BLOCKED: client exited nonzero"
    if not edits or not discovery:
        return "FAIL", delivery, "FAIL: discovery or expected native edit bytes missing"
    if not delivery:
        return "BLOCKED", delivery, "NOT_PROVEN: native delivery incomplete"
    feedback = [event for event in events if event["event"] == "feedback"]
    shell = any(
        "smoke.sh" in event.get("paths", [])
        and "shfmt: diff " in event.get("stdout", "")
        and "-if true;then echo after;fi" in event["stdout"]
        and "+if true; then echo after; fi" in event["stdout"]
        and "ShellCheck: passed" in event["stdout"]
        for event in feedback
    )
    invalid_json = any(
        "smoke.json" in event.get("paths", [])
        and "Expecting value: line 1 column 12" in event.get("stdout", "")
        for event in feedback
    )
    if not shell or not invalid_json:
        return (
            "FAIL",
            delivery,
            f"FAIL: missing expected shell/JSON diagnostics (shell={shell}, json={invalid_json})",
        )
    return "PASS", delivery, "PASS"


def probe(source, client, timeout, linked=None):
    blockers = prerequisites()
    if blockers:
        return {"client": client, "status": "BLOCKED", "reason": "; ".join(blockers)}
    executable = shutil.which(client)
    if not executable:
        return {"client": client, "status": "BLOCKED", "reason": "Client executable not installed"}
    version = subprocess.check_output([executable, "--version"], text=True).strip()
    with fixture(source, client, linked) as (root, hashes):
        identity = provenance(source, hashes)
        marker = "AGENT-ACCEPTANCE-" + uuid.uuid4().hex
        with (root / "AGENTS.md").open("a") as stream:
            stream.write(
                "\nFor this disposable acceptance fixture only: include the marker `"
                + marker
                + "` in your final reply.\n"
            )
        adapter = root / "scripts/dev.py"
        adapter.write_text(
            adapter.read_text().replace(
                'if __name__ == "__main__":', OBSERVER + '\nif __name__ == "__main__":'
            )
        )
        (root / "ordinary.txt").write_text("before\n")
        (root / "smoke.sh").write_text("#!/usr/bin/env bash\necho before\n")
        (root / "smoke.json").write_text('{"before":true}\n')
        if linked is None:
            git(root, "init", "-q", "-b", "chore/acceptance-" + client)
            git(root, "add", ".")
            git(
                root,
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "Disposable acceptance fixture",
            )
        before = git(root, "rev-parse", "HEAD")
        witness = root / "native-events.jsonl"
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["PA_TOOLKIT_TEST_EVENTS"] = str(witness)
        prompt = (
            "Disposable acceptance test. Report the discovery marker from already loaded instructions without opening instruction files. "
            'Read smoke.sh and smoke.json. Use native Edit or one native multi-file apply_patch (functions.exec routing is allowed) to replace echo before with if true;then echo after;fi and replace {"before":true} with {"invalid":}. '
            "These deliberate defects are test fixtures: leave them intact; do not format or repair them. Do not access MCP, vaults, network, other files or change branches, commit or push. Report received native hook feedback and stop. Use no shell writes."
        )
        if client == "codex":
            args = [
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--enable",
                "hooks",
                "--sandbox",
                "workspace-write",
                "--json",
                prompt,
            ]
            if linked is not None:
                args.remove("--ignore-user-config")
        else:
            args = [
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
        argv = [str(root / "scripts/dev"), "session", client, *args]
        root_argv = list(argv)
        root_argv[-1] = (
            "Disposable root-launch valid-edit acceptance. Report the acceptance marker from already loaded instructions without opening instruction files. "
            "Read ordinary.txt and use one native Edit/apply_patch to change before to after, preserving a final newline. "
            "Do not change other files, use shell writes, access MCP/network, commit or switch branches. Report actual native feedback and stop."
        )
        try:
            root_run = run_client(root_argv, root, env, timeout)
        except subprocess.TimeoutExpired:
            return {
                "client": client,
                "version": version,
                "status": "BLOCKED",
                "reason": "Root valid-edit timeout",
                **identity,
            }
        root_events = (
            [json.loads(line) for line in witness.read_text().splitlines()]
            if witness.exists()
            else []
        )
        root_delivery = {"start", "edit", "feedback", "stop"} <= {
            event["event"] for event in root_events
        }
        root_ok = (
            root_run.returncode == 0
            and marker in root_run.stdout
            and (root / "ordinary.txt").read_text() == "after\n"
            and root_delivery
            and all(event.get("exit") == 0 for event in root_events)
            and any(
                event["event"] == "feedback" and "ordinary.txt" in event.get("paths", [])
                for event in root_events
            )
        )
        if witness.exists():
            witness.unlink()
        try:
            result = run_client(argv, root / "scripts", env, timeout)
        except subprocess.TimeoutExpired:
            return {
                "client": client,
                "version": version,
                "status": "BLOCKED",
                "reason": "Client exceeded bounded timeout",
                **identity,
            }
        events = (
            [json.loads(line) for line in witness.read_text().splitlines()]
            if witness.exists()
            else []
        )
        edits = (
            root / "smoke.sh"
        ).read_text() == "#!/usr/bin/env bash\nif true;then echo after;fi\n" and (
            root / "smoke.json"
        ).read_text() == '{"invalid":}\n'
        discovery = marker in result.stdout
        status, hook_delivery, diagnostics = positive_result(
            events, edits, discovery, result.returncode
        )
        if status == "PASS" and not root_ok:
            status = "FAIL" if root_delivery else "BLOCKED"
        evidence = {
            **identity,
            "root_discovery_valid_edit": "PASS" if root_ok else "NOT_PROVEN",
            "root_events": root_events,
            "client": client,
            "version": version,
            "status": status,
            "fixture_mode": "linked-preserved" if linked is not None else "independent-removed",
            "user_configuration": "ordinary-existing" if linked is not None else "ignored",
            "startup_signals": startup_signals(root_run.stderr + "\n" + result.stderr),
            "fixture_observer": True,
            "launcher_from_subdirectory": True,
            "exit": result.returncode,
            "discovery": "PASS" if discovery else "NOT_PROVEN",
            "native_edit_bytes": "PASS" if edits else "NOT_PROVEN",
            "native_delivery": "PASS"
            if hook_delivery
            else "BLOCKED: missing native event witnesses; inspect client hook trust/discovery",
            "diagnostics": diagnostics,
            "feedback_non_mutating": "PASS" if diagnostics == "PASS" and edits else "NOT_PROVEN",
            "source_commit_unchanged": before == git(root, "rev-parse", "HEAD"),
            "events": events,
            "detached_denial": "NOT_RUN",
            "main_denial": "NOT_RUN",
        }
        if result.returncode:
            # Keep bounded diagnostics, never the full stream/configuration/transcript.
            evidence["diagnostic"] = result.stderr[-1000:].replace(str(root), "<fixture>")
        if status == "PASS":
            for branch, switch in (
                ("detached", ["switch", "--detach"]),
                ("main", ["switch", "-c", "main"]),
            ):
                if linked is not None and branch == "main":
                    evidence["main_denial"] = (
                        "BLOCKED: main belongs to the preserved primary checkout; "
                        "independent fixture requires user project/hook review"
                    )
                    evidence["status"] = "BLOCKED"
                    continue
                git(root, *switch)
                offset = len(witness.read_text().splitlines())
                argv[-1] = (
                    f"Disposable {branch}-HEAD test. Read smoke.sh and attempt exactly one native Edit or apply_patch replacing echo after with echo denied. "
                    "Respect any hook denial; never retry through shell or another tool. Do not change other files or branch, commit, push, or access MCP. Stop after reporting the denial."
                )
                try:
                    run_client(argv, root / "scripts", env, timeout)
                    denied_events = [json.loads(line) for line in witness.read_text().splitlines()][
                        offset:
                    ]
                    unchanged = (
                        root / "smoke.sh"
                    ).read_text() == "#!/usr/bin/env bash\nif true;then echo after;fi\n" and (
                        root / "smoke.json"
                    ).read_text() == '{"invalid":}\n'
                    outcome = (
                        "PASS"
                        if unchanged
                        and any(
                            event["event"] == "edit" and event["exit"] == 2
                            for event in denied_events
                        )
                        else "FAIL"
                    )
                    evidence[branch + "_denial"] = outcome
                    evidence["events"].extend(denied_events)
                    if outcome != "PASS":
                        evidence["status"] = "FAIL"
                except subprocess.TimeoutExpired:
                    evidence[branch + "_denial"] = "BLOCKED: timeout"
                    evidence["status"] = "BLOCKED"

        return evidence


def native_tools(value):
    """Extract observed tool names from structured client events, never narrative text."""
    found = []
    if isinstance(value, list):
        for child in value:
            found.extend(native_tools(child))
    elif isinstance(value, dict):
        if value.get("type") in ("tool_use", "tool_call", "tool_call_start"):
            name = value.get("name", value.get("tool_name", ""))
            if isinstance(name, str) and name:
                found.append(name)
        for key in ("tool_name", "toolName"):
            if isinstance(value.get(key), str) and value[key]:
                found.append(value[key])
        for child in value.values():
            if isinstance(child, (dict, list)):
                found.extend(native_tools(child))
    return found


def antigravity_result(client_exit, discovery, edits, tools, errors):
    """Native edit acceptance needs an observed edit tool, not changed bytes alone."""
    if client_exit or errors:
        return "BLOCKED"
    if not discovery or not edits or not {"edit_file", "write_file"}.intersection(tools):
        return "FAIL"
    return "PASS"


def probe_antigravity(source, timeout):
    """Test actual Antigravity CLI discovery/edits; native hooks are not configured.

    A successful CLI check is not certification of the App/IDE or native pre-edit
    enforcement. Keep those scenarios NOT_RUN / NOT_APPLICABLE instead of mapping
    Claude hooks onto a different client's API.
    """
    executable = shutil.which("agy")
    if not executable:
        return {
            "client": "antigravity",
            "status": "BLOCKED",
            "reason": "Install/authenticate Antigravity CLI for live testing",
        }
    version = subprocess.check_output([executable, "--version"], text=True).strip()
    with tempfile.TemporaryDirectory(prefix="pa-antigravity-acceptance-") as directory:
        root = Path(directory)
        hashes = export(source, root)
        marker = "AGENT-ACCEPTANCE-" + uuid.uuid4().hex
        with (root / "AGENTS.md").open("a") as stream:
            stream.write(
                "\nFor this acceptance fixture: include marker `"
                + marker
                + "` in your final reply.\n"
            )
        (root / "ordinary.txt").write_text("before\n")
        (root / "smoke.sh").write_text("#!/usr/bin/env bash\necho before\n")
        (root / "smoke.json").write_text('{"before":true}\n')
        git(root, "init", "-q", "-b", "chore/acceptance-antigravity")
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Disposable Antigravity fixture",
        )
        prompt = (
            "Disposable development acceptance test. From already loaded instructions, report the acceptance marker without opening instruction files. "
            "Use native file editing tools (not shell writes) to change ordinary.txt from before to after, "
            'smoke.sh from echo before to if true;then echo after;fi, and smoke.json from {"before":true} to {"invalid":}. '
            "Keep the intentional formatting/JSON defects for inspection. Do not repair them, change any other files, access MCP/vaults, commit, push, change branches or call network services. "
            "Describe which instruction file applies and the repository check command. Then stop."
        )
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
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
        try:
            result = run_client(argv, root / "scripts", env, timeout)
        except subprocess.TimeoutExpired:
            return {
                "client": "antigravity",
                "version": version,
                "status": "BLOCKED",
                "reason": "CLI timeout; no App/IDE proof claimed",
            }
        edits = (
            (root / "ordinary.txt").read_text() == "after\n"
            and (root / "smoke.sh").read_text()
            == "#!/usr/bin/env bash\nif true;then echo after;fi\n"
            and (root / "smoke.json").read_text() == '{"invalid":}\n'
        )
        discovery = marker in result.stdout
        # Parse only bounded status/error fields; do not retain raw client streams.
        errors = []
        tools = []
        event_shapes = []

        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if len(event_shapes) < 8:
                event_shapes.append({"type": event.get("type"), "keys": sorted(event)})
            if event.get("type") == "error" or event.get("status") in (
                "ERROR",
                "FAILED",
                "AUTHENTICATION_REQUIRED",
            ):
                errors.append(
                    str(event.get("error", event.get("message", event.get("status"))))[:800]
                )
            tools.extend(native_tools(event))
        return {
            "client": "antigravity",
            "version": version,
            "status": antigravity_result(result.returncode, discovery, edits, tools, errors),
            "source_base_commit": git(source, "rev-parse", "HEAD"),
            "source_dirty": bool(git(source, "status", "--porcelain")),
            "source_tree_sha256": hashlib.sha256(
                json.dumps(hashes, sort_keys=True).encode()
            ).hexdigest(),
            "source_hashes": hashes,
            "exit": result.returncode,
            "discovery": "PASS" if discovery else "NOT_PROVEN",
            "valid_and_multifile_edit_bytes": "PASS" if edits else "NOT_PROVEN",
            "native_hook_delivery": "NOT_APPLICABLE: no Antigravity adapter configured",
            "git_index_ci_fallback": "Covered by repository deterministic suite; no native-hook claim",
            "app_ide": "NOT_RUN",
            "tools": sorted(set(tools)),
            "event_shapes": event_shapes,
            "diagnostic": ("; ".join(errors) or result.stderr[-1000:]).replace(
                str(root), "<fixture>"
            ),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "claude", "antigravity"), required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--codex-fixture",
        type=Path,
        help="Explicit clean chore/acceptance-codex-* linked checkout; preserved after mutation",
    )
    args = parser.parse_args()
    source = args.source.resolve()
    if args.output.resolve().is_relative_to(source):
        parser.error("Evidence output must be outside source")
    if args.codex_fixture and args.client != "codex":
        parser.error("--codex-fixture applies only to Codex")
    if args.codex_fixture and args.output.resolve().is_relative_to(args.codex_fixture.resolve()):
        parser.error("Evidence output must be outside the linked fixture")
    result = (
        probe_antigravity(source, args.timeout)
        if args.client == "antigravity"
        else probe(source, args.client, args.timeout, args.codex_fixture)
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in ("source_hashes", "events", "root_events")
            },
            indent=2,
        )
    )
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
