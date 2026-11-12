"""Exercise the full concurrency CLI with deterministic clients, never model credentials."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STUB = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import re
import sys
import time

if "--version" in sys.argv:
    print("fixture-agy")
    raise SystemExit(0)

root = Path.cwd()
prompt = sys.argv[sys.argv.index("-p") + 1]
expected = re.search(r"replace before with (after-[a-z]+)", prompt)[1]
marker = re.search(r"AGENT-ACCEPTANCE-[a-f0-9]+", (root / "AGENTS.md").read_text())[0]
(root / "ordinary.txt").write_text(expected + "\\n")
if os.environ["PA_TEST_EXTRA_FILE"] == "1":
    (root / " unexpected \\nfile.txt").write_text("unexpected\\n")
    (root / "unexpected-dir").mkdir()
    (root / "unexpected-dir/nested.txt").write_text("unexpected\\n")

# A bounded rendezvous guarantees overlapping child processes without a timing guess.
barrier = Path(os.environ["PA_TEST_RENDEZVOUS"])
(barrier / expected).touch()
deadline = time.monotonic() + 5
while len(list(barrier.iterdir())) < 2:
    if time.monotonic() > deadline:
        raise SystemExit("fixture rendezvous timed out")
    time.sleep(0.01)
print(json.dumps({"type": "tool_use", "name": "edit_file"}))
print(json.dumps({"type": "message", "text": marker}))
"""


class ConcurrencyCliTests(unittest.TestCase):
    def test_untracked_extra_files_fail_and_are_retained_in_both_session_receipts(self):
        with tempfile.TemporaryDirectory(prefix="pa-concurrency-regression-") as directory:
            temp = Path(directory)
            binaries = temp / "bin"
            binaries.mkdir()
            stub = binaries / "agy"
            stub.write_text(STUB)
            stub.chmod(0o755)
            for extra in (False, True):
                with self.subTest(extra=extra):
                    barrier = temp / ("extra" if extra else "valid")
                    barrier.mkdir()
                    output = temp / (barrier.name + ".json")
                    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
                    env.update(
                        PATH=str(binaries) + os.pathsep + env.get("PATH", ""),
                        PA_TEST_EXTRA_FILE="1" if extra else "0",
                        PA_TEST_RENDEZVOUS=str(barrier),
                    )
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts/verify-agent-concurrency.py"),
                            "--output",
                            str(output),
                        ],
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode, 1 if extra else 0, result.stderr)
                    receipt = json.loads(output.read_text())
                    expected = "FAIL" if extra else "PASS"
                    self.assertEqual(receipt["status"], expected)
                    self.assertTrue(receipt["independent_branches"])
                    self.assertGreater(receipt["overlap_seconds"], 0)
                    self.assertEqual(len(receipt["sessions"]), 2)
                    for session in receipt["sessions"]:
                        self.assertTrue(session["discovery"])
                        self.assertTrue(session["exact_bytes"])
                        self.assertEqual(session["tools"], ["edit_file"])
                        self.assertEqual(session["status"], expected)
                        paths = ["AGENTS.md", "ordinary.txt"]
                        if extra:
                            paths += [" unexpected \nfile.txt", "unexpected-dir/nested.txt"]
                        self.assertEqual(sorted(session["changed_paths"]), sorted(paths))
