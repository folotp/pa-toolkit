"""Shared engine contracts: no vault, finance, hosted writes or model calls."""

import copy
import hashlib
import importlib.util
import json
import os
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pa_devtools import planning, specifications

ROOT = Path(__file__).resolve().parents[1]

SPEC = importlib.util.spec_from_file_location("toolkit_ci_adapter", ROOT / "scripts/dev.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class CIIntegrationTests(unittest.TestCase):
    """Exercise adapter selection/execution, keeping remote proof a controlled fixture."""

    def test_docs_bump_and_code_use_actual_policy_and_archive_decision(self):
        original_git = adapter.git
        original_run = subprocess.run
        for paths, skipped, archive in (
            (["docs/development.md"], {"code", "tests"}, False),
            ([".claude-plugin/plugin.json"], {"code", "tests"}, True),
            (["skills/plugin-release/scripts/release.py"], set(), True),
        ):
            with self.subTest(paths=paths), contextlib.ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        adapter,
                        "git",
                        side_effect=lambda *args: ""
                        if args == ("status", "--porcelain")
                        else original_git(*args),
                    )
                )
                stack.enter_context(patch.object(planning, "changed_paths", return_value=paths))
                stack.enter_context(
                    patch.object(planning, "trusted_github_base", return_value=True)
                )
                stack.enter_context(patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}))
                commands = []

                def gate_run(argv, *args, **kwargs):
                    if argv[:2] == ["./scripts/dev", "_gate"]:
                        commands.append(argv)
                        return subprocess.CompletedProcess(argv, 0)
                    return original_run(argv, *args, **kwargs)

                stack.enter_context(patch.object(planning.subprocess, "run", side_effect=gate_run))
                package = stack.enter_context(patch.object(adapter, "package"))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                adapter.ci("a" * 40)
                self.assertEqual(
                    {cmd[-1] for cmd in commands if cmd[:2] == ["./scripts/dev", "_gate"]},
                    set(adapter.development_policy()["gates"]) - skipped,
                )
                self.assertEqual(package.called, archive)

    def test_main_schedule_dispatch_force_full_even_with_trusted_base(self):
        for event in ("push", "schedule", "workflow_dispatch"):
            with (
                self.subTest(event=event),
                patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": event}),
                patch.object(planning, "changed_paths", return_value=["docs/a.md"]),
                patch.object(planning, "trusted_github_base", return_value=True) as trust,
            ):
                self.assertTrue(adapter.ci_plan("a" * 40)["full"])
                trust.assert_not_called()

    def test_actual_workflow_shell_routes_pr_and_main_without_interpolating_input(self):
        import yaml

        workflow = yaml.safe_load((ROOT / ".github/workflows/release-checks.yml").read_text())
        step = workflow["jobs"]["checks"]["steps"][-1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            script = root / "scripts/dev"
            script.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > args\n')
            script.chmod(0o755)
            for event, expected in (
                ("pull_request", ["ci", "--base", "a" * 40]),
                ("push", ["ci", "--full"]),
                ("schedule", ["ci", "--full"]),
            ):
                env = dict(os.environ, TOOLKIT_EVENT=event, TOOLKIT_BASE="a" * 40)
                subprocess.run(["bash", "-eu", "-c", step["run"]], cwd=root, env=env, check=True)
                self.assertEqual((root / "args").read_text().splitlines(), expected)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "config/development.json").read_text())

    def test_docs_only_skips_code_and_tests_but_keeps_required_checks(self):
        plan = planning.classify(self.policy, ["docs/development.md"])
        self.assertFalse(plan["full"])
        self.assertEqual(set(plan["skip"]), {"code", "tests"})
        self.assertTrue(
            {"doctor", "specs", "spec-freshness", "links", "inventory", "package-contract"}
            <= set(plan["run"])
        )

    def test_version_bump_skips_unaffected_code_tests(self):
        plan = planning.classify(self.policy, [".claude-plugin/plugin.json", "README.md"])
        self.assertEqual(set(plan["skip"]), {"code", "tests"})
        self.assertIn("runtime-metadata", plan["classes"])
        self.assertIn("specs", plan["run"])
        self.assertIn("package-contract", plan["run"])

    def test_unknown_deleted_moved_and_policy_inputs_are_full(self):
        for names in (
            ["new/unknown.md"],
            ["README.md", "deleted.py"],
            ["docs/new.md", "old.sh"],
            ["tools/pa-devtools/pyproject.toml"],
            ["config/development.json"],
            [".github/workflows/release-checks.yml"],
        ):
            with self.subTest(names=names):
                plan = planning.classify(self.policy, names)
                self.assertFalse(plan["skip"])
                self.assertTrue("tests" in plan["run"])

    def test_missing_base_and_explicit_full_never_select_partial(self):
        for plan in (
            planning.classify(self.policy, None),
            planning.classify(self.policy, ["docs/a.md"], "release/full main validation"),
        ):
            self.assertTrue(plan["full"])
            self.assertFalse(plan["skip"])
        for name in ("../outside.md", "/absolute.md", ""):
            with self.assertRaises(ValueError):
                planning.classify(self.policy, [name])

    def test_malformed_policy_or_unknown_gate_fails_closed(self):
        for field, value in [("schema_version", True), ("gates", []), ("changes", [])]:
            policy = copy.deepcopy(self.policy)
            policy[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                planning.classify(policy, [])
        policy = copy.deepcopy(self.policy)
        policy["changes"][0]["gates"] = ["nonexistent"]
        with self.assertRaises(ValueError):
            planning.classify(policy, ["docs/a.md"])

    def test_executor_runs_only_declared_gates_and_propagates_failure(self):
        policy = copy.deepcopy(self.policy)
        for name, rule in policy["gates"].items():
            rule["argv"] = ["fixture", name]
        plan = planning.classify(policy, ["docs/a.md"])
        with patch.object(planning.subprocess, "run") as run:
            planning.execute(ROOT, policy, plan)
        self.assertEqual([call.args[0][1] for call in run.call_args_list], plan["run"])
        with (
            patch.object(
                planning.subprocess, "run", side_effect=subprocess.CalledProcessError(8, "fixture")
            ),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            planning.execute(ROOT, policy, plan)


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.git("init", "-q", "-b", "main")
        (self.root / "policy.json").write_text("reviewed")
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )
        self.base = self.git("rev-parse", "HEAD")
        self.valid = {
            "head_sha": self.base,
            "head_branch": "main",
            "event": "push",
            "path": ".github/workflows/checks.yml",
            "status": "completed",
            "conclusion": "success",
        }

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, env=self.env, text=True
        ).strip()

    def trusted(self, runs=None, fetch=None):
        return planning.trusted_github_base(
            self.root,
            self.base,
            "owner/repo",
            ".github/workflows/checks.yml",
            ["policy.json"],
            fetch=fetch or (lambda url: {"workflow_runs": runs}),
        )

    def test_only_completed_full_main_push_workflow_is_trusted(self):
        self.assertTrue(self.trusted([self.valid]))
        for field, value in [
            ("head_sha", "a" * 40),
            ("head_branch", "feat/fixture"),
            ("event", "pull_request"),
            ("path", ".github/workflows/other.yml"),
            ("status", "in_progress"),
            ("conclusion", "failure"),
        ]:
            invalid = dict(self.valid, **{field: value})
            with self.subTest(field=field):
                self.assertFalse(self.trusted([invalid]))
        self.assertFalse(self.trusted([]))
        self.assertFalse(self.trusted(fetch=lambda url: {}))
        self.assertFalse(self.trusted(fetch=lambda url: {"workflow_runs": [None]}))

        def blocked(url):
            raise OSError("network blocked")

        self.assertFalse(self.trusted(fetch=blocked))

    def test_changed_policy_or_missing_history_cannot_reuse_baseline(self):
        (self.root / "policy.json").write_text("changed")
        self.assertFalse(self.trusted([self.valid]))
        self.base = "b" * 40
        self.assertFalse(self.trusted([self.valid]))

    def test_changed_engine_directory_and_nonancestor_base_are_not_trusted(self):
        (self.root / "engine").mkdir()
        (self.root / "engine/core.py").write_text("reviewed = True\n")
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "engine baseline",
        )
        base = self.git("rev-parse", "HEAD")
        valid = dict(self.valid, head_sha=base)

        def trusted():
            return planning.trusted_github_base(
                self.root,
                base,
                "owner/repo",
                ".github/workflows/checks.yml",
                ["engine"],
                fetch=lambda url: {"workflow_runs": [valid]},
            )

        self.assertTrue(trusted())
        (self.root / "engine/core.py").write_text("reviewed = False\n")
        self.assertFalse(trusted())
        self.git("restore", "engine/core.py")
        self.git("checkout", "-q", "--detach", self.base)
        self.assertFalse(trusted())

    def test_diff_reports_both_rename_paths_and_missing_base_is_full(self):
        self.git("mv", "policy.json", "renamed.md")
        self.git(
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "rename",
        )
        self.assertEqual(
            set(planning.changed_paths(self.root, self.base)), {"policy.json", "renamed.md"}
        )
        self.assertIsNone(planning.changed_paths(self.root, "b" * 40))
        self.assertIsNone(planning.changed_paths(self.root, None))


class SpecificationTests(unittest.TestCase):
    def test_official_core_detects_real_constraints(self):
        values = {"name": "fixture", "description": "Valid fixture"}
        self.assertEqual(specifications.validate_skill(values, Path("fixture"), "portable"), [])
        for bad in (
            dict(values, name="UPPER"),
            dict(values, description="x" * 1025),
            dict(values, compatibility="x" * 501),
            dict(values, metadata={"count": 3}),
            dict(values, typo="bad"),
            dict(values, name=7),
            dict(values, description=False),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                specifications.validate_skill(bad, Path("fixture"), "portable")

    def test_known_claude_fields_are_reported_not_silently_ignored(self):
        values = {
            "name": "fixture",
            "description": "Valid fixture",
            "argument-hint": "[path]",
            "disable-model-invocation": True,
            "allowed-tools": ["Read", "Bash"],
        }
        result = specifications.validate_skill(values, Path("fixture"), "claude")
        self.assertIn("argument-hint", result)
        self.assertIn("allowed-tools array -> string", result)
        with self.assertRaisesRegex(ValueError, "Unsupported skill fields"):
            specifications.validate_skill(values, Path("fixture"), "portable")
        with self.assertRaises(ValueError):
            specifications.validate_skill(dict(values, unknown=True), Path("fixture"), "claude")

    def test_official_plugin_schema_and_legacy_envelope_boundary(self):
        legacy = {"name": "fixture", "version": "1.0.0"}
        self.assertTrue(specifications.validate_manifest(legacy, "claude"))
        with self.assertRaisesRegex(ValueError, "schema"):
            specifications.validate_manifest(legacy, "portable")
        portable = dict(
            legacy, **{"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"}
        )
        self.assertEqual(specifications.validate_manifest(portable, "portable"), [])
        for bad in (
            dict(portable, author=[]),
            dict(portable, unknown=True),
            dict(portable, name="bad--name"),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                specifications.validate_manifest(bad, "portable")

    def inventory(self, content=b"current"):
        return {
            "sources": {
                "source": {
                    "url": "https://official.invalid/spec",
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            }
        }

    def test_freshness_requires_current_hash_and_available_network(self):
        with patch.object(specifications, "pins", return_value=self.inventory()):
            specifications.check_latest(fetch=lambda url: b"current")
            with self.assertRaisesRegex(ValueError, "Upstream drift"):
                specifications.check_latest(fetch=lambda url: b"changed")

            def blocked(url):
                raise ValueError("required upstream check unavailable")

            with self.assertRaisesRegex(ValueError, "unavailable"):
                specifications.check_latest(fetch=blocked)

    def test_published_version_is_not_highest_working_draft(self):
        inventory = {
            "sources": {
                "status": {"url": "https://official.invalid/status", "published_version": "1.0.0"}
            }
        }
        with patch.object(specifications, "pins", return_value=inventory):
            specifications.check_latest(
                fetch=lambda url: b"Agent Plugins Specification 1.0.0 is the current published release. 1.1.0 is a working draft."
            )
            with self.assertRaisesRegex(ValueError, "published"):
                specifications.check_latest(
                    fetch=lambda url: b"Agent Plugins Specification 1.1.0 is the current published release."
                )

    def test_vendored_schema_is_hash_verified(self):
        original = specifications.vendor_text

        def modified(name):
            value = original(name)
            return value + " " if name == "plugin.schema.json" else value

        with (
            patch.object(specifications, "vendor_text", side_effect=modified),
            self.assertRaisesRegex(ValueError, "reviewed hash"),
        ):
            specifications.validate_manifest({"name": "fixture"}, "claude")


if __name__ == "__main__":
    unittest.main()
