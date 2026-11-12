"""Current authoritative resolution, moving standards and visible failure contracts."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pa_devtools import live_specs

ROOT = Path(__file__).resolve().parents[1]


class LiveSpecificationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config/specifications.json").read_text())

    def fetch(self, url):
        if url.endswith("/README.md") and "agent-plugins-spec" in url:
            return b"Agent Plugins Specification 2.3.4 is the current published release. 9.0.0 is a working draft."
        if url.endswith("plugin.schema.json"):
            return json.dumps(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$id": "https://official.invalid/current.schema.json",
                    "type": "object",
                    "required": ["name"],
                }
            ).encode()
        return b"Current official prose, including editorial changes"

    def test_resolves_new_published_version_and_current_revisions_without_repins(self):
        def revision(url):
            return "a" * 40 if "agentskills" in url else "b" * 40

        evidence, schema = live_specs.resolve(self.config, self.fetch, revision)
        self.assertEqual(evidence["plugin_version"], "2.3.4")
        self.assertEqual(evidence["skills_ref_commit"], "a" * 40)
        self.assertIn(
            "/" + "b" * 40 + "/schemas/2.3.4/", evidence["sources"]["plugin-schema"]["url"]
        )
        self.assertEqual(schema["required"], ["name"])
        self.assertEqual(evidence["sources"]["agents-md"]["kind"], "prose-only")

    def test_unknown_publication_or_unavailable_source_fails_without_pinned_fallback(self):
        for fetch in (lambda url: b"Only a working draft is available", lambda url: b""):
            with self.assertRaises(ValueError):
                live_specs.resolve(self.config, fetch, lambda url: "a" * 40)

        def unavailable(url):
            raise OSError("Network unavailable")

        with self.assertRaises(OSError):
            live_specs.resolve(self.config, unavailable, lambda url: "a" * 40)

    def test_latest_reference_dependency_and_child_environment(self):
        evidence, schema = live_specs.resolve(self.config, self.fetch, lambda url: "c" * 40)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config/specifications.json").write_text(json.dumps(self.config))
            (root / ".claude-plugin").mkdir()
            (root / ".claude-plugin/plugin.json").write_text('{"name":"fixture"}')
            skill = root / "skills/fixture"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: fixture\ndescription: Valid fixture\nargument-hint: path\n---\nBody\n"
            )
            with (
                patch.object(live_specs, "resolve", return_value=(copy.deepcopy(evidence), schema)),
                patch.dict(live_specs.os.environ, {"GH_TOKEN": "fixture-not-a-secret"}),
                patch.object(live_specs.subprocess, "run") as run,
            ):
                result = live_specs.check(root)
            self.assertIn("@" + "c" * 40 + "#subdirectory=skills-ref", run.call_args.args[0][4])
            self.assertNotIn("GH_TOKEN", run.call_args.kwargs["env"])
            self.assertEqual(result["results"]["prose_semantics"], "MANUAL_REVIEW")
            changed_schema = dict(schema, required=["new-upstream-required-field"])
            with (
                patch.object(
                    live_specs, "resolve", return_value=(copy.deepcopy(evidence), changed_schema)
                ),
                self.assertRaisesRegex(ValueError, "new-upstream"),
            ):
                live_specs.check(root)


if __name__ == "__main__":
    unittest.main()
