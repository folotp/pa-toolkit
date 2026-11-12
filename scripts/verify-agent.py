"""Reusable real-client acceptance probe in an independent disposable repository.

Exports selected source bytes (including current WIP) without modifying its index.
Only deterministic fixture outcomes and bounded native-hook observations are retained;
raw client streams are temporary. No trust, sandbox or Git-hook bypass is permitted.
A fixture-only observer wraps the unchanged hook function, not client configuration.
An absent observer record means native delivery was not proven, regardless of what
an agent says. Missing clients/authentication or untrusted hooks are explicit blockers.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
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
        item = {"event":event,"tool":payload.get("tool_name"),"exit":code,
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


def probe(source, client, timeout):
    executable = shutil.which(client)
    if not executable:
        return {"client": client, "status": "BLOCKED", "reason": "Client executable not installed"}
    version = subprocess.check_output([executable, "--version"], text=True).strip()
    with tempfile.TemporaryDirectory(prefix="pa-agent-acceptance-") as directory:
        root = Path(directory)
        hashes = export(source, root)
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
        (root / "smoke.sh").write_text("#!/usr/bin/env bash\necho before\n")
        (root / "smoke.json").write_text('{"before":true}\n')
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
        try:
            result = run_client(argv, root / "scripts", env, timeout)
        except subprocess.TimeoutExpired:
            return {
                "client": client,
                "version": version,
                "status": "BLOCKED",
                "reason": "Client exceeded bounded timeout",
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
        observed = {e["event"] for e in events}
        discovery = marker in result.stdout
        hook_delivery = {"start", "edit", "feedback", "stop"} <= observed
        status = (
            "PASS"
            if result.returncode == 0 and edits and discovery and hook_delivery
            else "BLOCKED"
        )
        if result.returncode == 0 and (not edits or not discovery):
            status = "FAIL"
        evidence = {
            "client": client,
            "version": version,
            "status": status,
            "source_commit": git(source, "rev-parse", "HEAD"),
            "source_hashes": hashes,
            "fixture_observer": True,
            "launcher_from_subdirectory": True,
            "exit": result.returncode,
            "discovery": "PASS" if discovery else "NOT_PROVEN",
            "native_edit_bytes": "PASS" if edits else "NOT_PROVEN",
            "native_delivery": "PASS"
            if hook_delivery
            else "BLOCKED: missing native event witnesses; inspect client hook trust/discovery",
            "feedback_non_mutating": "PASS" if edits and "feedback" in observed else "NOT_PROVEN",
            "source_commit_unchanged": before == git(root, "rev-parse", "HEAD"),
            "events": events,
            "detached_denial": "NOT_RUN",
        }
        if result.returncode:
            # Keep bounded diagnostics, never the full stream/configuration/transcript.
            evidence["diagnostic"] = result.stderr[-1000:].replace(str(root), "<fixture>")
        if hook_delivery and edits:
            git(root, "switch", "--detach")
            denial = "Disposable detached-HEAD test. Read smoke.sh and attempt exactly one native Edit or apply_patch replacing echo after with echo denied. Respect any hook denial; never retry through shell or another tool. Do not change other files or branch, commit, push, or access MCP. Stop after reporting the denial."
            argv[-1] = denial
            try:
                run_client(argv, root / "scripts", env, timeout)
                denied_events = [json.loads(line) for line in witness.read_text().splitlines()][
                    len(events) :
                ]
                unchanged = (
                    root / "smoke.sh"
                ).read_text() == "#!/usr/bin/env bash\nif true;then echo after;fi\n"
                evidence["detached_denial"] = (
                    "PASS"
                    if unchanged
                    and any(e["event"] == "edit" and e["exit"] == 2 for e in denied_events)
                    else "FAIL"
                )
                evidence["events"].extend(denied_events)
                if evidence["detached_denial"] != "PASS":
                    evidence["status"] = "FAIL"
            except subprocess.TimeoutExpired:
                evidence["detached_denial"] = "BLOCKED: timeout"
                evidence["status"] = "BLOCKED"
        return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "claude"), required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    source = args.source.resolve()
    if args.output.resolve().is_relative_to(source):
        parser.error("Evidence output must be outside source")
    result = probe(source, args.client, args.timeout)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key not in ("source_hashes", "events")},
            indent=2,
        )
    )
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
