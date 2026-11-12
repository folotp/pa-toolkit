"""Probe acceptance must prove diagnostics, not only event-name coverage."""

import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agent_probe", ROOT / "scripts/verify-agent.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class PositiveAcceptanceTests(unittest.TestCase):
    def events(self):
        return [
            {"event": "start", "exit": 0},
            {"event": "edit", "exit": 0, "paths": ["smoke.sh"]},
            {
                "event": "feedback",
                "exit": 0,
                "paths": ["smoke.sh"],
                "stdout": "shfmt: diff <fixture>/smoke.sh.orig <fixture>/smoke.sh\n-if true;then echo after;fi\n+if true; then echo after; fi\nShellCheck: passed",
            },
            {"event": "edit", "exit": 0, "paths": ["smoke.json"]},
            {
                "event": "feedback",
                "exit": 0,
                "paths": ["smoke.json"],
                "stdout": "Expecting value: line 1 column 12 (char 11)",
            },
            {"event": "stop", "exit": 0},
        ]

    def test_only_successful_hooks_with_both_path_diagnostics_pass(self):
        self.assertEqual(
            probe.positive_result(self.events(), True, True, 0), ("PASS", True, "PASS")
        )

    def test_event_names_without_diagnostics_cannot_pass(self):
        events = self.events()
        for event in events:
            event.pop("stdout", None)
        self.assertEqual(probe.positive_result(events, True, True, 0)[0], "FAIL")

    def test_feedback_for_only_one_file_or_wrong_paths_fails(self):
        for changed in (
            [e for e in self.events() if e.get("paths") != ["smoke.json"]],
            self.events(),
        ):
            if len(changed) == 6:
                changed[4]["paths"] = ["wrong.json"]
            self.assertEqual(probe.positive_result(changed, True, True, 0)[0], "FAIL")

    def test_nonzero_positive_hook_cannot_pass(self):
        for index in range(len(self.events())):
            events = copy.deepcopy(self.events())
            events[index]["exit"] = 2
            self.assertEqual(probe.positive_result(events, True, True, 0)[0], "FAIL")

    def test_missing_or_runtime_unavailable_diagnostic_tool_is_blocked(self):
        self.assertEqual(
            probe.positive_result(self.events(), True, True, 0, ["Install shfmt"])[0], "BLOCKED"
        )
        events = self.events()
        events[2]["stdout"] = "shfmt: [Errno 2] No such file or directory: shfmt"
        self.assertEqual(probe.positive_result(events, True, True, 0)[0], "BLOCKED")
        with patch.object(probe.shutil, "which", return_value=None):
            self.assertTrue(any("Install shfmt" in error for error in probe.prerequisites()))

    def test_native_delivery_absence_is_not_a_pass(self):
        self.assertEqual(probe.positive_result([], True, True, 0)[0], "BLOCKED")


class AntigravityAcceptanceTests(unittest.TestCase):
    def test_native_edit_proof_is_required_independently_of_bytes(self):
        self.assertEqual(
            probe.antigravity_result(0, True, True, ["read_file", "edit_file"], []), "PASS"
        )
        self.assertEqual(probe.antigravity_result(0, True, True, ["run_command"], []), "FAIL")
        self.assertEqual(
            probe.antigravity_result(1, False, False, [], ["Authentication required"]), "BLOCKED"
        )
