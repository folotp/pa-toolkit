"""Probe acceptance must prove diagnostics, not only event-name coverage."""

import copy
from contextlib import nullcontext
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agent_probe", ROOT / "scripts/verify-agent.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class PositiveAcceptanceTests(unittest.TestCase):
    def test_linked_main_blocker_preserves_an_observed_detached_guard_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("Fixture instructions\n")
            (root / "scripts").mkdir()
            (root / "scripts/dev.py").write_text('if __name__ == "__main__":\n    pass\n')
            calls = []

            def client(argv, cwd, env, timeout):
                calls.append(argv)
                witness = Path(env["PA_TOOLKIT_TEST_EVENTS"])
                marker = probe.re.search(
                    r"AGENT-ACCEPTANCE-[a-f0-9]+", (root / "AGENTS.md").read_text()
                )[0]
                if len(calls) == 1:
                    (root / "ordinary.txt").write_text("after\n")
                    events = [
                        {"event": event, "exit": 0, "paths": ["ordinary.txt"]}
                        for event in ("start", "edit", "feedback", "stop")
                    ]
                    witness.write_text("".join(json.dumps(e) + "\n" for e in events))
                elif len(calls) == 2:
                    (root / "smoke.sh").write_text(
                        "#!/usr/bin/env bash\nif true;then echo after;fi\n"
                    )
                    (root / "smoke.json").write_text('{"invalid":}\n')
                    witness.write_text("".join(json.dumps(e) + "\n" for e in self.events()))
                else:
                    # Simulate an actual guard regression: native edit succeeds on detached HEAD.
                    (root / "smoke.sh").write_text("#!/usr/bin/env bash\necho denied\n")
                    with witness.open("a") as stream:
                        stream.write(
                            json.dumps({"event": "edit", "exit": 0, "paths": ["smoke.sh"]}) + "\n"
                        )
                return subprocess.CompletedProcess(argv, 0, marker, "")

            with (
                patch.object(probe, "fixture", return_value=nullcontext((root, {}))),
                patch.object(probe, "git", return_value="fixture-head"),
                patch.object(probe, "prerequisites", return_value=[]),
                patch.object(probe.shutil, "which", return_value="codex"),
                patch.object(probe.subprocess, "check_output", return_value="codex fixture"),
                patch.object(probe, "run_client", side_effect=client),
            ):
                result = probe.probe(root, "codex", 1, linked=root / "selected-fixture")
            self.assertEqual(result["root_discovery_valid_edit"], "PASS")
            self.assertEqual(result["diagnostics"], "PASS")
            self.assertEqual(result["detached_denial"], "FAIL")
            self.assertTrue(result["main_denial"].startswith("BLOCKED"))
            self.assertEqual(result["status"], "FAIL")

            # Independent mode can reach main after a failed detached edit; a later
            # timeout must not hide that already observed regression either.
            calls.clear()
            (root / "AGENTS.md").write_text("Fixture instructions\n")

            def main_timeout(argv, cwd, env, timeout):
                if len(calls) == 3:
                    raise subprocess.TimeoutExpired("codex", timeout)
                return client(argv, cwd, env, timeout)

            with (
                patch.object(probe, "fixture", return_value=nullcontext((root, {}))),
                patch.object(probe, "git", return_value="fixture-head"),
                patch.object(probe, "prerequisites", return_value=[]),
                patch.object(probe.shutil, "which", return_value="codex"),
                patch.object(probe.subprocess, "check_output", return_value="codex fixture"),
                patch.object(probe, "run_client", side_effect=main_timeout),
            ):
                result = probe.probe(root, "codex", 1)
            self.assertEqual(result["diagnostics"], "PASS")
            self.assertEqual(result["detached_denial"], "FAIL")
            self.assertEqual(result["main_denial"], "BLOCKED: timeout")
            self.assertEqual(result["status"], "FAIL")

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
    def test_only_structured_tool_names_are_retained(self):
        events = [
            {"content": [{"type": "tool_use", "name": "edit_file"}]},
            {"toolName": "read_file"},
            {"type": "message", "text": "I used edit_file"},
            {"type": "tool_call", "name": None},
        ]
        self.assertEqual(probe.native_tools(events), ["edit_file", "read_file"])

    def test_native_edit_proof_is_required_independently_of_bytes(self):
        self.assertEqual(
            probe.antigravity_result(0, True, True, ["read_file", "edit_file"], []), "PASS"
        )
        self.assertEqual(probe.antigravity_result(0, True, True, ["run_command"], []), "FAIL")
        self.assertEqual(
            probe.antigravity_result(1, False, False, [], ["Authentication required"]), "BLOCKED"
        )


class LinkedFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(
            os.environ,
            {k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            clear=True,
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.source = Path(self.temp.name) / "source"
        self.source.mkdir()
        probe.git(self.source, "init", "-q", "-b", "feat/source")
        (self.source / "tracked.txt").write_text("original\n")
        (self.source / ".codex").mkdir()
        (self.source / ".codex/hooks.json").write_text('{"hooks": {}}\n')
        probe.git(self.source, "add", ".")
        probe.git(
            self.source,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )
        self.linked = Path(self.temp.name) / "linked"
        probe.git(
            self.source,
            "worktree",
            "add",
            "-q",
            "-b",
            "chore/acceptance-codex-test",
            str(self.linked),
        )

    def test_wip_export_and_branch_restore_preserve_fixture_and_index(self):
        before = probe.git(self.linked, "write-tree")
        (self.source / "tracked.txt").write_text("selected WIP\n")
        with self.assertRaises(subprocess.TimeoutExpired):
            with probe.fixture(self.source, "codex", self.linked) as (root, hashes):
                self.assertEqual(root, self.linked.resolve())
                self.assertEqual((root / "tracked.txt").read_text(), "selected WIP\n")
                self.assertTrue(probe.provenance(self.source, hashes)["source_dirty"])
                probe.git(root, "switch", "--detach")
                raise subprocess.TimeoutExpired("client", 1)
        self.assertTrue(self.linked.exists())
        self.assertEqual(
            probe.git(self.linked, "branch", "--show-current"), "chore/acceptance-codex-test"
        )
        self.assertEqual(probe.git(self.linked, "write-tree"), before)
        self.assertEqual((self.source / "tracked.txt").read_text(), "selected WIP\n")

    def test_source_wrong_client_or_ordinary_branch_refused_before_export(self):
        for client, target in (("codex", self.source), ("claude", self.linked)):
            with self.assertRaises(ValueError):
                with probe.fixture(self.source, client, target):
                    self.fail("unsafe fixture accepted")
        probe.git(self.linked, "switch", "-c", "feat/preserved")
        with self.assertRaisesRegex(ValueError, "branch must start"):
            with probe.fixture(self.source, "codex", self.linked):
                self.fail("ordinary checkout accepted")

    def test_untracked_or_staged_work_refused_and_preserved(self):
        (self.linked / "user.txt").write_text("preserve\n")
        for stage in (False, True):
            if stage:
                probe.git(self.linked, "add", "user.txt")
            with self.assertRaisesRegex(ValueError, "must be clean"):
                with probe.fixture(self.source, "codex", self.linked):
                    self.fail("dirty fixture accepted")
            self.assertEqual((self.linked / "user.txt").read_text(), "preserve\n")

    def test_different_source_head_refused_before_export(self):
        probe.git(
            self.source,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "new source",
        )
        with self.assertRaisesRegex(ValueError, "source HEAD"):
            with probe.fixture(self.source, "codex", self.linked):
                self.fail("different fixture HEAD accepted")

    def test_startup_categories_retain_no_arbitrary_stderr(self):
        self.assertEqual(
            probe.startup_signals(
                "Project config.toml files are disabled. Open /hooks for review. token=secret"
            ),
            ["project_layer_disabled", "hook_review_required"],
        )
        self.assertEqual(probe.startup_signals("unrelated private output"), [])

    def test_source_deletion_or_changed_linked_bindings_refused_before_export(self):
        (self.source / "tracked.txt").unlink()
        with self.assertRaisesRegex(ValueError, "source deletions"):
            with probe.fixture(self.source, "codex", self.linked):
                self.fail("stale linked HEAD file would remain")
        self.assertEqual((self.linked / "tracked.txt").read_text(), "original\n")
        (self.source / "tracked.txt").write_text("original\n")
        (self.linked / ".codex/hooks.json").write_text('{"hooks": {"Stop": []}}\n')
        probe.git(self.source, "branch", "-m", "chore/acceptance-codex-primary")
        # Source can itself be a linked feature checkout, with different primary bindings.
        with self.assertRaisesRegex(ValueError, "Changed hook definitions"):
            with probe.fixture(self.linked, "codex", self.source):
                self.fail("old primary bindings would be certified")

    def test_staged_source_removal_refused_without_leaving_a_stale_file(self):
        probe.git(self.source, "rm", "tracked.txt")
        with self.assertRaisesRegex(ValueError, "source deletions"):
            with probe.fixture(self.source, "codex", self.linked):
                self.fail("staged removal would leave a stale linked file")
        self.assertEqual((self.linked / "tracked.txt").read_text(), "original\n")

    def test_staged_source_rename_refused_without_leaving_the_old_path(self):
        probe.git(self.source, "mv", "tracked.txt", "renamed.txt")
        with self.assertRaisesRegex(ValueError, "source deletions"):
            with probe.fixture(self.source, "codex", self.linked):
                self.fail("staged rename would leave the old linked path")
        self.assertEqual((self.linked / "tracked.txt").read_text(), "original\n")
        self.assertFalse((self.linked / "renamed.txt").exists())
