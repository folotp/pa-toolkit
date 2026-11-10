"""Development contracts in disposable repos; no user index, vault or client required."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dev", SOURCE / "scripts/dev.py")
dev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="toolkit-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo with spaces"
        self.root.mkdir()
        self.original_root = dev.ROOT
        dev.ROOT = self.root
        self.addCleanup(setattr, dev, "ROOT", self.original_root)
        # Prevent parent Git hook variables from escaping into fixture repositories.
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.environment = patch.dict(os.environ, clean, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Fixture")
        self.write("ordinary.py", "value = 1\n")
        self.commit()
        self.git("switch", "-q", "-c", "chore/test")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def commit(self):
        self.git("add", ".")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture")

    def index_fixture(self):
        # A real parser in the exported checkout, rather than a mocked check result.
        # Avoid recursively invoking this test suite from its own check-staged test.
        script = self.write(
            "scripts/dev",
            "#!/bin/sh\nexec python3 -c \"import ast,pathlib; ast.parse(pathlib.Path('ordinary.py').read_text())\"\n",
        )
        script.chmod(0o755)
        self.git("add", ".")

    def test_staged_content_cannot_be_hidden_by_unstaged_repair(self):
        self.index_fixture()
        self.write("ordinary.py", "value = (\n")
        self.git("add", "ordinary.py")
        self.write("ordinary.py", "value = 2\n")
        with self.assertRaises(subprocess.CalledProcessError):
            dev.check_staged()
        self.assertEqual(self.git("show", ":ordinary.py"), "value = (")
        self.assertEqual((self.root / "ordinary.py").read_text(), "value = 2\n")

    def test_unstaged_invalid_content_does_not_poison_valid_index(self):
        self.index_fixture()
        self.write("ordinary.py", "value = (\n")
        before = self.git("status", "--porcelain")
        dev.check_staged()
        self.assertEqual(self.git("status", "--porcelain"), before)

    def test_staged_addition_deletion_modes_and_git_environment_isolation(self):
        script = self.write(
            "scripts/dev",
            "#!/bin/sh\nset -eu\ntest ! -e ordinary.py\ntest -x added.sh\ntest -f added.py\ntest -z \"${GIT_INDEX_FILE:-}\"\npython3 -c \"import subprocess; assert 'added.py' in subprocess.check_output(['git','ls-files'],text=True)\"\n",
        )
        script.chmod(0o755)
        self.git("rm", "-q", "ordinary.py")
        added = self.write("added.sh", "#!/bin/sh\nexit 0\n")
        added.chmod(0o755)
        self.write("added.py", "pass\n")
        self.git("add", ".")
        # Git sets these when executing hooks. The export must strip them only for
        # the isolated subprocesses, without mutating the caller's environment.
        index = str(self.root / ".git/index")
        with patch.dict(os.environ, {"GIT_INDEX_FILE": index}):
            dev.check_staged()
            self.assertEqual(os.environ["GIT_INDEX_FILE"], index)

    def test_staged_main_and_detached_denied(self):
        for ref in ("main", "--detach"):
            self.git("switch", "-q", ref)
            with self.assertRaisesRegex(ValueError, "main/detached"):
                dev.check_staged()

    def test_unmerged_index_fails_without_export(self):
        # Direct index conflict fixture, leaving the working file unchanged.
        blob = self.git("rev-parse", "HEAD:ordinary.py")
        subprocess.run(
            ["git", "update-index", "--index-info"],
            cwd=self.root,
            input=f"0 {'0' * 40}\tordinary.py\n100644 {blob} 1\tordinary.py\n100644 {blob} 2\tordinary.py\n",
            text=True,
            check=True,
        )
        with self.assertRaises(subprocess.CalledProcessError):
            dev.check_staged()

    def test_unmanaged_hook_preflights_both_before_any_write(self):
        first = self.write(".git/hooks/pre-commit", dev.hook_text("pre-commit"))
        other = self.write(".git/hooks/pre-push", "#!/bin/sh\necho custom\n")
        before = first.read_bytes(), other.read_bytes()
        with self.assertRaisesRegex(ValueError, "unmanaged"):
            dev.install_hooks()
        self.assertEqual(before, (first.read_bytes(), other.read_bytes()))

    def test_marker_does_not_authorize_discarding_user_commands(self):
        hook = self.write(
            ".git/hooks/pre-commit",
            "#!/bin/sh\n"
            + dev.LEGACY_MARKER
            + "\nexec python3 /tmp/branch-guard.py pre-commit\necho custom\n",
        )
        with self.assertRaisesRegex(ValueError, "unmanaged"):
            dev.install_hooks()
        self.assertIn("echo custom", hook.read_text())

    def test_legacy_managed_guards_migrate_and_uninstall_is_exact(self):
        for event in ("pre-commit", "pre-push"):
            self.write(
                ".git/hooks/" + event,
                "#!/bin/sh\n"
                + dev.LEGACY_MARKER
                + "\nexec python3 "
                + shlex.quote("/tmp/path with spaces/branch-guard.py")
                + " "
                + event
                + "\n",
            )
        dev.install_hooks()
        for event in ("pre-commit", "pre-push"):
            self.assertEqual(dev.hook_file(event).read_text(), dev.hook_text(event))
        dev.install_hooks(uninstall=True)
        self.assertFalse(dev.hook_file("pre-commit").exists())
        self.assertFalse(dev.hook_file("pre-push").exists())

    def test_hook_symlinks_preserved(self):
        target = self.write("custom-hook", "user content")
        (self.root / ".git/hooks/pre-commit").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            dev.install_hooks()
        self.assertEqual(target.read_text(), "user content")

    def test_relative_and_absolute_core_hooks_path(self):
        for location in (".custom-hooks", str(Path(self.temp.name) / "shared hooks")):
            self.git("config", "core.hooksPath", location)
            dev.install_hooks()
            self.assertTrue(dev.hook_file("pre-commit").is_file())
            self.assertTrue(dev.hook_file("pre-push").is_file())

    def test_shared_hook_resolves_invoking_linked_checkout(self):
        other = Path(self.temp.name) / "linked worktree"
        self.git("worktree", "add", "-q", "-b", "chore/linked", str(other))
        for root in (self.root, other):
            launcher = root / "scripts/dev"
            launcher.parent.mkdir(exist_ok=True)
            launcher.write_text('#!/bin/sh\nprintf "%s\\n%s\\n" "$PWD" "$1"\n')
            launcher.chmod(0o755)
        dev.ROOT = other
        dev.install_hooks()
        for root in (self.root, other):
            result = subprocess.check_output(
                [str(dev.hook_file("pre-commit"))], cwd=root, text=True
            )
            self.assertEqual(Path(result.splitlines()[0]).resolve(), root.resolve())
            self.assertEqual(result.splitlines()[1], "check-staged")
        (other / "scripts/dev").unlink()
        result = subprocess.run(
            [str(dev.hook_file("pre-commit"))], cwd=other, text=True, capture_output=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Shared checks missing", result.stderr)

    def test_push_main_destination_multiple_updates_and_malformed_fail(self):
        for records in (
            "refs/heads/feat/a abc refs/heads/main def\n",
            "refs/heads/a abc refs/heads/a def\nrefs/heads/a abc refs/heads/main def\n",
            "malformed\n",
        ):
            dev.ROOT = SOURCE
            with self.assertRaises(ValueError):
                dev.pre_push(io.StringIO(records))
        dev.pre_push(io.StringIO("refs/heads/a abc refs/heads/a def\n"))
        dev.pre_push(io.StringIO(""))  # No updates is a valid Git no-op.

    def test_yaml_ambiguous_duplicate_unsafe_and_wrong_shapes_fail(self):
        for body in (
            "name: a\ndescription: bad: value",
            "name: a\nname: b",
            "- one\n- two",
            "!!python/object:os.system {}",
        ):
            path = self.write("component.md", "---\n" + body + "\n---\nBody\n")
            with self.subTest(body=body), self.assertRaises(ValueError):
                dev.frontmatter(path)

    def test_claude_frontmatter_supported_fields_and_wrong_types(self):
        path = self.write(
            "component.md",
            '---\nname: a\ndescription: >-\n  Valid: colon and \\"quotes\\".\nargument-hint: "[path]"\ndisable-model-invocation: true\nallowed-tools: [Bash, Read]\n---\nBody\n',
        )
        values = dev.frontmatter(path)
        self.assertIs(values["disable-model-invocation"], True)
        self.assertEqual(values["allowed-tools"], ["Bash", "Read"])
        with self.assertRaisesRegex(ValueError, "invalid/missing disabled"):
            dev.validate_fields(
                {"disabled": "false"}, {"disabled": lambda v: type(v) is bool}, {}, "fixture"
            )
        with self.assertRaisesRegex(ValueError, "unsupported"):
            dev.validate_fields({"new": True}, {}, {}, "fixture")

    def test_links_reference_images_encoded_targets_and_examples(self):
        self.write("space name.md", "exists")
        self.write(
            "note.md",
            "[ok][ref]\n\n[ref]: space%20name.md\n\n`[fake](missing.md)`\n\n```md\n[example](absent.md)\n```\n\n[[Vault note]]\n",
        )
        dev.links()
        self.write("note.md", "![missing](absent.png)\n")
        with self.assertRaisesRegex(ValueError, "absent.png"):
            dev.links()

    def test_hook_multi_file_moves_deletes_subdir_and_outside(self):
        (self.root / "sub").mkdir()
        payload = {
            "tool_name": "apply_patch",
            "cwd": str(self.root / "sub"),
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: ../ordinary.py\n*** Move to: ../renamed.py\n@@\n-x\n+y\n*** Delete File: ../old.py\n*** Add File: ../added.py\n+x\n*** End Patch"
            },
        }
        self.assertEqual(
            {p.name for p in dev.hook_paths(payload)},
            {"ordinary.py", "renamed.py", "old.py", "added.py"},
        )
        payload["tool_input"]["command"] = (
            "*** Begin Patch\n*** Add File: ../../outside\n+x\n*** End Patch"
        )
        with self.assertRaisesRegex(ValueError, "outside repository"):
            dev.hook_paths(payload)
        (self.root / "escape").symlink_to(Path(self.temp.name))
        with self.assertRaisesRegex(ValueError, "outside repository"):
            dev.hook_paths(
                {
                    "tool_name": "Write",
                    "cwd": str(self.root),
                    "tool_input": {"file_path": "escape/private"},
                }
            )

    def test_hook_rejects_unsupported_or_malformed_payload(self):
        for payload in (
            [],
            {},
            {"tool_input": []},
            {"tool_name": "apply_patch", "tool_input": {"command": "bad"}},
            {"tool_name": "Bash", "tool_input": {"command": "echo x"}},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                dev.hook_paths(payload)

    def test_feedback_is_bounded_and_does_not_rewrite(self):
        path = self.write("fixture.sh", "#!/bin/bash\nif true;then echo after;fi\n")
        original = path.read_bytes()
        payload = {
            "tool_name": "Edit",
            "cwd": str(self.root),
            "tool_input": {"file_path": str(path)},
        }
        output = io.StringIO()
        with (
            patch("sys.stdin", io.StringIO(json.dumps(payload))),
            contextlib.redirect_stdout(output),
        ):
            dev.hook("feedback")
        message = json.loads(output.getvalue())["hookSpecificOutput"]["additionalContext"]
        self.assertIn("files unchanged", message)
        self.assertIn("fixture.sh", message)
        self.assertLessEqual(len(message), 4000)
        self.assertEqual(path.read_bytes(), original)

    def test_stop_skips_repeat_and_empty_failed_tools_are_not_passed(self):
        with (
            patch("sys.stdin", io.StringIO('{"stop_hook_active":true}')),
            patch.object(dev, "source_files") as files,
        ):
            dev.hook("stop")
            files.assert_not_called()
        with patch.object(
            dev.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "")
        ):
            self.assertIn("failed without diagnostic", dev.advisory(["fixture"]))

    def test_session_launch_normalizes_subdirectory_and_preserves_arguments(self):
        launcher = self.root / "scripts/dev"
        launcher.parent.mkdir()
        shutil.copy2(SOURCE / "scripts/dev", launcher)
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        client = fake_bin / "codex"
        client.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@"\n')
        client.chmod(0o755)
        output = subprocess.check_output(
            [str(launcher), "session", "codex", "--example", "argument with spaces"],
            cwd=launcher.parent,
            env=dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ["PATH"]),
            text=True,
        )
        self.assertEqual(Path(output.splitlines()[0]).resolve(), self.root.resolve())
        self.assertEqual(output.splitlines()[1:], ["--example", "argument with spaces"])

    def test_package_excludes_untracked_ignored_development_and_local_clutter(self):
        self.write(".gitignore", "*.bak\ndist/\n")
        runtime = self.write("skills/example/SKILL.md", "runtime")
        self.write("skills/example/secret.bak", "private")
        self.write("skills/example/untracked.txt", "private")
        self.write("dist/old.skill", "private")
        self.write("config/package-files.json", json.dumps(["skills/example/SKILL.md"]))
        self.git("add", "skills/example/SKILL.md")
        self.assertEqual(dev.package_paths(), [runtime])
        for name in (
            "dist/old.skill",
            ".codex/hooks.json",
            "../outside",
            str(runtime),
            "skills/example/untracked.txt",
        ):
            self.write("config/package-files.json", json.dumps([name]))
            with self.subTest(name=name), self.assertRaises(ValueError):
                dev.package_paths()

    def test_package_symlink_duplicate_missing_and_wrong_policy_fail(self):
        (self.root / "leak").symlink_to(Path(self.temp.name) / "outside")
        for names in (["leak"], ["ordinary.py", "ordinary.py"], ["missing"], None, {}, []):
            self.write("config/package-files.json", json.dumps(names))
            with self.subTest(names=names), self.assertRaises(ValueError):
                dev.package_paths()

    def test_real_archive_from_selected_source_has_exact_bytes(self):
        # Build from a real linked-worktree fixture, not a mocked ZIP invocation.
        other = Path(self.temp.name) / "package worktree"
        self.git("worktree", "add", "-q", "-b", "chore/package", str(other))
        dev.ROOT = other
        manifest = other / ".claude-plugin/plugin.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({"name": "fixture", "version": "1.0.0"}))
        (other / "config").mkdir()
        (other / "config/package-files.json").write_text(json.dumps([".claude-plugin/plugin.json"]))
        subprocess.run(["git", "add", "."], cwd=other, check=True)
        output = Path(self.temp.name) / "out"
        with patch.object(dev, "package_check"):
            dev.package(SOURCE / "skills/plugin-release/scripts/package.sh", output)
        with zipfile.ZipFile(output / "fixture-v1.0.0.plugin") as archive:
            files = {n for n in archive.namelist() if not n.endswith("/")}
            self.assertEqual(files, {".claude-plugin/plugin.json"})
            self.assertEqual(archive.read(".claude-plugin/plugin.json"), manifest.read_bytes())
        with self.assertRaisesRegex(ValueError, "outside source"):
            dev.package(SOURCE / "skills/plugin-release/scripts/package.sh", other / "dist")

    def test_strict_json_duplicate_keys_and_nonfinite_numbers(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                dev.parse_json(text)
        self.assertEqual(dev.parse_json('{"a":1}'), {"a": 1})

    def test_edit_on_main_or_detached_is_denied_without_protected_files(self):
        payload = {
            "tool_name": "Edit",
            "cwd": str(self.root),
            "tool_input": {"file_path": str(self.root / "ordinary.py")},
        }
        with patch("sys.stdin", io.StringIO(json.dumps(payload))):
            dev.hook("edit")
        self.git("switch", "-q", "main")
        with (
            patch("sys.stdin", io.StringIO(json.dumps(payload))),
            self.assertRaisesRegex(ValueError, "feature worktree"),
        ):
            dev.hook("edit")

    def test_version_banners_and_unparseable_output(self):
        for output, expected in [
            ("git version 2.54.0 (Apple Git)", (2, 54, 0)),
            ("shfmt v3.6.0", (3, 6, 0)),
            ("ShellCheck\nversion: 0.9.0", (0, 9, 0)),
            ("jq-1.6", (1, 6, 0)),
            ("Copyright 1990-2008\nZip 3.0", (3, 0, 0)),
        ]:
            self.assertEqual(dev.parse_version(output), expected)
        with self.assertRaises(ValueError):
            dev.parse_version("unrecognized")

    def test_doctor_missing_old_broken_and_supported_tools(self):
        self.write(
            "config/toolchain.json",
            json.dumps({"shfmt": {"minimum": "3.6.0", "flag": "--version"}}),
        )
        for found, version, code, okay in [
            (None, "3.6.0", 0, False),
            ("/tool", "3.5.0", 0, False),
            ("/tool", "v3.6.0", 1, False),
            ("/tool", "unknown", 0, False),
            ("/tool", "v3.6.0", 0, True),
        ]:
            with (
                patch.object(dev.shutil, "which", return_value=found),
                patch.object(
                    dev.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], code, version),
                ),
                patch.object(dev, "run", return_value="3.11.18"),
                patch.object(dev, "hook_file", return_value=self.root / "absent"),
            ):
                if okay:
                    dev.doctor()
                else:
                    with self.assertRaises(ValueError):
                        dev.doctor()

    def test_blocked_managed_environment_fails_actionably(self):
        self.write(
            "config/toolchain.json",
            json.dumps({"shfmt": {"minimum": "3.6.0", "flag": "--version"}}),
        )
        with (
            patch.object(dev.shutil, "which", return_value="/tool"),
            patch.object(
                dev.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "v3.6.0")
            ),
            patch.object(dev, "run", side_effect=OSError("cache denied")),
            patch.object(dev, "hook_file", return_value=self.root / "absent"),
            self.assertRaisesRegex(ValueError, "uv sync --locked"),
        ):
            dev.doctor()


if __name__ == "__main__":
    unittest.main()
