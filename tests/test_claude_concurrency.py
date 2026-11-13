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

if mode == "auth-error":
    print(json.dumps({"type":"error", "message":"deterministic authentication required"}), flush=True)
    raise SystemExit(1)
if mode in ("timeout-clean", "timeout-read-instructions"):
    if mode == "timeout-read-instructions":
        print(json.dumps({"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":str(root/"AGENTS.md")}}]}}), flush=True)
    time.sleep(60)

def hook(event, name, payload):
    env = dict(os.environ)
    if mode == "missing-receipts":
        env.pop("PA_TOOLKIT_HOOK_TRACE", None)
    result = subprocess.run([str(root / "scripts/dev"), "hook", event], input=json.dumps(payload),
                            text=True, capture_output=True, env=env, check=True)
    code = 2 if mode == "bad-native-exit" and event == "feedback" else result.returncode
    output = "diagnostic suppressed" if mode == "missing-diagnostics" and event == "feedback" else result.stdout
    print(json.dumps({"type":"system","subtype":"hook_response","hook_event":name,
                      "stdout":output,"stderr":result.stderr,"exit_code":code,"outcome":"success",
                      "hook_name":name+(":Edit" if event in ("edit","feedback") else "")}))

hook("start", "SessionStart", {})
for name, content in [("ordinary.txt", expected+"\n"),
                      ("smoke.sh", "#!/usr/bin/env bash\nif true;then echo after;fi\n"),
                      ("smoke.json", '{"invalid":}\n')]:
    payload = {"tool_name":"Edit","tool_input":{"file_path":str(root/name)}}
    print(json.dumps({"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":str(root/name)}}]}}))
    hook("edit", "PreToolUse", payload)
    if mode == "corrupt-client-error" and name == "ordinary.txt":
        content = "unexpected bytes\n"
    (root/name).write_text(content)
    hook("feedback", "PostToolUse", payload)
hook("stop", "Stop", {})
print(json.dumps({"type":"assistant","message":{"content":[{"type":"text","text":marker}]}}))
if mode == "extra-edit":
    print(json.dumps({"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":str(root/"ordinary.txt")}}]}}))
if mode == "wrong-receipt-tool":
    trace = Path(os.environ["PA_TOOLKIT_HOOK_TRACE"])
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    for record in records:
        if record["event"] in ("edit", "feedback"):
            record["tool"] = "Write"
    trace.write_text("".join(json.dumps(record)+"\n" for record in records))
if mode == "deleted-client-error":
    (root/"ordinary.txt").unlink()
if mode in ("corrupt-client-error", "deleted-client-error"):
    raise SystemExit(1)

"""


class ClaudeConcurrencyTests(unittest.TestCase):
    def witness(self):
        targets = ("ordinary.txt", "smoke.sh", "smoke.json")
        calls = [{"tool": "Edit", "path": name} for name in targets]
        events = ["start", "edit", "feedback", "edit", "feedback", "edit", "feedback", "stop"]
        receipts = [
            {
                "event": name,
                "tool": "Edit" if name in {"edit", "feedback"} else None,
                "exit": 0,
                "outcome": "completed",
            }
            for name in events
        ]
        native_names = {
            "start": "SessionStart",
            "edit": "PreToolUse",
            "feedback": "PostToolUse",
            "stop": "Stop",
        }
        responses = [
            {
                "hook_event": native_names[name],
                "hook_name": native_names[name] + (":Edit" if name in {"edit", "feedback"} else ""),
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

    def test_each_edit_requires_its_own_matching_hook_tool_sequence(self):
        calls, responses, receipts = self.witness()

        def outcome(calls=calls, responses=responses, receipts=receipts, code=0):
            return runner.claude_outcome(code, True, True, calls, responses, receipts, [])

        self.assertEqual(outcome(calls=calls + [calls[0]]), "FAIL")
        self.assertEqual(outcome(calls=calls + [calls[0]], code=1), "FAIL")
        wrong_tool = copy.deepcopy(receipts)
        wrong_tool[1]["tool"] = "Write"
        self.assertEqual(outcome(receipts=wrong_tool), "FAIL")
        wrong_native = copy.deepcopy(responses)
        wrong_native[1]["hook_name"] = "PreToolUse:Write"
        self.assertEqual(outcome(responses=wrong_native), "FAIL")
        swapped = copy.deepcopy(receipts)
        swapped[1], swapped[2] = swapped[2], swapped[1]
        self.assertEqual(outcome(receipts=swapped), "FAIL")
        swapped_native = copy.deepcopy(responses)
        swapped_native[1], swapped_native[2] = swapped_native[2], swapped_native[1]
        self.assertEqual(outcome(responses=swapped_native), "FAIL")
        self.assertEqual(outcome(receipts=receipts[:-1]), "BLOCKED")
        self.assertEqual(outcome(receipts=receipts + [receipts[-1]]), "FAIL")

    def test_timeout_stream_preserves_text_or_older_byte_output(self):
        self.assertEqual(runner.timeout_stream(None), "")
        self.assertEqual(runner.timeout_stream("observed"), "observed")
        self.assertEqual(runner.timeout_stream(b"observed\xff"), "observed\ufffd")

    def test_unfinished_bytes_are_distinct_from_corruption_or_deletion(self):
        before = {"ordinary.txt": "before\n"}
        after = {"ordinary.txt": "after\n"}
        self.assertEqual(runner.fixture_bytes_outcome(before, after, before), (False, False))
        self.assertEqual(runner.fixture_bytes_outcome(before, after, after), (True, False))
        self.assertEqual(
            runner.fixture_bytes_outcome(before, after, {"ordinary.txt": "wrong\n"}), (False, True)
        )
        self.assertEqual(
            runner.fixture_bytes_outcome(before, after, {"ordinary.txt": None}), (False, True)
        )

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
                ("auth-error", "BLOCKED"),
                ("timeout-clean", "BLOCKED"),
                ("timeout-read-instructions", "FAIL"),
                ("bad-native-exit", "FAIL"),
                ("missing-diagnostics", "FAIL"),
                ("extra-edit", "FAIL"),
                ("wrong-receipt-tool", "FAIL"),
                ("corrupt-client-error", "FAIL"),
                ("deleted-client-error", "FAIL"),
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
                            "--timeout",
                            "3" if mode.startswith("timeout-") else "20",
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
                        self.assertEqual(
                            len(session["native_calls"]),
                            {
                                "extra-edit": 4,
                                "auth-error": 0,
                                "timeout-clean": 0,
                                "timeout-read-instructions": 1,
                            }.get(mode, 3),
                        )
