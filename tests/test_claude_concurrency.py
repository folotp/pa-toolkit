"""Deterministic runner controls; fake CLI/manual hook calls are NOT native evidence."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "concurrency", ROOT / "scripts/verify-agent-concurrency.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

STUB = r"""#!/usr/bin/env python3
import json, os, re, subprocess, sys, time
from pathlib import Path
if "--version" in sys.argv:
    print("deterministic-claude-stub; NOT native evidence")
    raise SystemExit(0)
root = Path.cwd()
prompt = sys.argv[-1]
expected = re.search(r"replace before with (after-[a-z]+)", prompt)[1]
marker = re.search(r"AGENT-ACCEPTANCE-[a-f0-9]+", (root / "AGENTS.md").read_text())[0]
mode = os.environ["PA_TEST_CLAUDE_MODE"]
barrier = Path(os.environ["PA_TEST_RENDEZVOUS"])
(barrier / expected).touch()
deadline = time.monotonic() + 5
while len(list(barrier.iterdir())) < 2:
    if time.monotonic() > deadline:
        raise SystemExit("deterministic rendezvous timed out")
    time.sleep(.01)

def hook(event, name, payload):
    env = dict(os.environ)
    if mode == "missing-receipts":
        env.pop("PA_TOOLKIT_HOOK_TRACE", None)
    result = subprocess.run([str(root / "scripts/dev"), "hook", event], input=json.dumps(payload),
                            text=True, capture_output=True, env=env, check=True)
    code = 2 if mode == "bad-native-exit" and event == "feedback" else result.returncode
    output = "diagnostic suppressed" if mode == "missing-diagnostics" and event == "feedback" else result.stdout
    print(json.dumps({"type":"system","subtype":"hook_response","hook_event":name,
                      "stdout":output,"stderr":result.stderr,"exit_code":code,"outcome":"success"}))

hook("start", "SessionStart", {})
for name, content in [("ordinary.txt", expected+"\n"),
                      ("smoke.sh", "#!/usr/bin/env bash\nif true;then echo after;fi\n"),
                      ("smoke.json", '{"invalid":}\n')]:
    payload = {"tool_name":"Edit","tool_input":{"file_path":str(root/name)}}
    print(json.dumps({"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":str(root/name)}}]}}))
    hook("edit", "PreToolUse", payload)
    (root/name).write_text(content)
    hook("feedback", "PostToolUse", payload)
hook("stop", "Stop", {})
print(json.dumps({"type":"assistant","message":{"content":[{"type":"text","text":marker}]}}))
"""


class ClaudeConcurrencyTests(unittest.TestCase):
    def witness(self):
        targets = ("ordinary.txt", "smoke.sh", "smoke.json")
        calls = [{"tool": "Edit", "path": name} for name in targets]
        events = ["start", "edit", "feedback", "edit", "feedback", "edit", "feedback", "stop"]
        receipts = [{"event": name, "exit": 0, "outcome": "completed"} for name in events]
        native_names = {
            "start": "SessionStart",
            "edit": "PreToolUse",
            "feedback": "PostToolUse",
            "stop": "Stop",
        }
        responses = [
            {
                "hook_event": native_names[name],
                "stdout": "shfmt: smoke.sh; Expecting value" if name == "feedback" else "",
                "exit_code": 0,
                "outcome": "success",
            }
            for name in events
        ]
        return calls, responses, receipts

    def test_native_outcomes_and_missing_telemetry(self):
        calls, responses, receipts = self.witness()

        def outcome(calls=calls, responses=responses, receipts=receipts, code=0):
            return runner.claude_outcome(code, True, True, calls, responses, receipts, [])

        self.assertEqual(outcome(), "PASS")
        self.assertEqual(outcome(receipts=[]), "BLOCKED")
        self.assertEqual(outcome(responses=[]), "BLOCKED")
        self.assertEqual(outcome(responses=responses[:-1]), "BLOCKED")
        self.assertEqual(outcome(calls=calls + [{"tool": "Read", "path": "AGENTS.md"}]), "FAIL")
        bad = copy.deepcopy(responses)
        bad[1]["exit_code"] = 2
        self.assertEqual(outcome(responses=bad, code=1), "FAIL")
        missing = copy.deepcopy(responses)
        for response in missing:
            response["stdout"] = "model narrative is not hook diagnostic proof"
        self.assertEqual(outcome(responses=missing), "FAIL")

    def test_timeout_never_hides_head_or_extra_path_changes(self):
        self.assertFalse(
            runner.session_violation(
                ["AGENTS.md"], ["AGENTS.md", "ordinary.txt"], "before", "before", True
            )
        )
        self.assertTrue(
            runner.session_violation(
                ["AGENTS.md"], ["AGENTS.md", "ordinary.txt"], "before", "after", True
            )
        )
        self.assertTrue(
            runner.session_violation(
                ["AGENTS.md", "extra"], ["AGENTS.md"], "before", "before", True
            )
        )

    def test_native_stream_excludes_model_prose_and_redacts_resolved_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = [
                {
                    "type": "assistant",
                    "message": {
                        "content": [{"type": "text", "text": "shfmt: smoke.sh; Expecting value"}]
                    },
                },
                {
                    "type": "system",
                    "subtype": "hook_response",
                    "hook_event": "PostToolUse",
                    "stdout": str(root.resolve() / "smoke.sh"),
                    "exit_code": 0,
                },
            ]
            calls, responses, _ = runner.claude_witnesses(events, root)
            self.assertEqual(calls, [])
            self.assertEqual(responses[0]["stdout"], "<fixture>/smoke.sh")
            self.assertIsInstance(responses[0]["exit_code"], int)

    def test_fake_cli_complete_receipt_and_failure_controls(self):
        with tempfile.TemporaryDirectory(prefix="pa-claude-concurrency-control-") as directory:
            temp = Path(directory)
            binary = temp / "bin"
            binary.mkdir()
            stub = binary / "claude"
            stub.write_text(STUB)
            stub.chmod(0o755)
            for mode, expected in [
                ("normal", "PASS"),
                ("missing-receipts", "BLOCKED"),
                ("bad-native-exit", "FAIL"),
                ("missing-diagnostics", "FAIL"),
            ]:
                with self.subTest(mode=mode):
                    barrier = temp / mode
                    barrier.mkdir()
                    output = temp / (mode + ".json")
                    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
                    env.update(
                        PATH=str(binary) + os.pathsep + env.get("PATH", ""),
                        PA_TEST_RENDEZVOUS=str(barrier),
                        PA_TEST_CLAUDE_MODE=mode,
                    )
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts/verify-agent-concurrency.py"),
                            "--client",
                            "claude",
                            "--output",
                            str(output),
                        ],
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(
                        result.returncode, 0 if expected == "PASS" else 1, result.stderr
                    )
                    receipt = json.loads(output.read_text())
                    self.assertEqual(receipt["status"], expected)
                    self.assertTrue(receipt["source_unchanged"])
                    self.assertTrue(receipt["independent_branches"])
                    self.assertGreater(receipt["overlap_seconds"], 0)
                    for session in receipt["sessions"]:
                        self.assertEqual(session["status"], expected)
                        self.assertEqual(len(session["native_calls"]), 3)
