"""Exercise release contracts in disposable fixtures; never publish or use a vault."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('release', ROOT / 'skills/plugin-release/scripts/release.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo with spaces'
        self.root.mkdir()
        self.output = Path(self.temp.name) / 'out with spaces'
        self.packager = ROOT / 'skills/plugin-release/scripts/package.sh'
        self.write('plugin.json', json.dumps({'name': 'example', 'version': '1.0.0'}))
        self.write('.gitignore', '*.plugin\nprivate.secret\n')
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True)

    def test_fallback_dry_run_build_and_ignored_files(self):
        self.write('private.secret', 'never ship')
        self.write('untracked.txt', 'never ship')
        result = release.execute(self.root, self.output, self.packager, True)
        self.assertIsNone(result['archive'])
        self.assertFalse(self.output.exists())
        result = release.execute(self.root, self.output, self.packager)
        import zipfile
        with zipfile.ZipFile(result['archive']) as archive:
            self.assertNotIn('private.secret', archive.namelist())
            self.assertNotIn('untracked.txt', archive.namelist())
        self.assertTrue(Path(result['archive']).is_absolute())

    def extension(self, preflight):
        self.write('config/release.json', json.dumps({'schema_version': 1, 'preflight': preflight,
            'package': ['python3', 'package.py', '{packager}', '{output}']}))
        self.write('package.py', "import pathlib, subprocess, sys, shutil\nsubprocess.run(['bash', sys.argv[1], '.'], check=True)\nshutil.move('example-v1.0.0.plugin', pathlib.Path(sys.argv[2]) / 'example-v1.0.0.plugin')\n")

    def test_extension_used_identically_in_both_modes(self):
        self.extension(['python3', '-c', 'print("preflight")'])
        before = self.git('status', '--porcelain')
        for dry in (True, False):
            result = release.execute(self.root, self.output, self.packager, dry)
            self.assertEqual(result['dry_run'], dry)
            self.assertEqual(self.git('status', '--porcelain'), before)

    def test_extension_preserves_literal_braces_in_both_commands_and_modes(self):
        import shutil
        # Replacement values are paths and must not be expanded a second time.
        selected = Path(self.temp.name) / 'packager {output}' / 'package.sh'
        selected.parent.mkdir()
        shutil.copy2(self.packager, selected)
        self.packager = selected
        self.extension(['python3', '-c',
            "import json, sys; assert {'valid': True}['valid']; assert json.loads(sys.argv[1]) == {'message': '{literal}'}; assert sys.argv[2] == '{unknown}'; assert sys.argv[3] == 'regex{2,4}'",
            '{"message":"{literal}"}', '{unknown}', 'regex{2,4}'])
        config = json.loads((self.root / 'config/release.json').read_text())
        config['package'].append('{"package":"literal"}')
        self.write('config/release.json', json.dumps(config))
        script = self.root / 'package.py'
        script.write_text(script.read_text() + "assert sys.argv[3] == '{\"package\":\"literal\"}'\n")
        for dry in (True, False):
            with self.subTest(dry=dry):
                result = release.execute(self.root, self.output, self.packager, dry)
                self.assertEqual(result['dry_run'], dry)

    def test_failed_required_extension_blocks_both_modes(self):
        self.extension(['python3', '-c', 'raise SystemExit(9)'])
        for dry in (True, False):
            with self.assertRaises(subprocess.CalledProcessError):
                release.execute(self.root, self.output, self.packager, dry)
        self.assertFalse(self.output.exists())

    def test_nonobject_extension_never_falls_back_in_either_mode(self):
        for content in ('null', '[]', 'true', '0', '"extension"'):
            self.write('config/release.json', content)
            for dry in (True, False):
                with self.subTest(content=content, dry=dry):
                    with self.assertRaisesRegex(ValueError, 'must be an object'):
                        release.execute(self.root, self.output, self.packager, dry)
                    self.assertFalse(self.output.exists())

    def test_bad_extension_never_falls_back(self):
        self.write('config/release.json', '{"schema_version":99}')
        with self.assertRaises(ValueError):
            release.execute(self.root, self.output, self.packager)


if __name__ == '__main__':
    unittest.main()
