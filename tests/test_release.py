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

    def test_failed_required_extension_blocks_both_modes(self):
        self.extension(['python3', '-c', 'raise SystemExit(9)'])
        for dry in (True, False):
            with self.assertRaises(subprocess.CalledProcessError):
                release.execute(self.root, self.output, self.packager, dry)
        self.assertFalse(self.output.exists())

    def test_bad_extension_never_falls_back(self):
        self.write('config/release.json', '{"schema_version":99}')
        with self.assertRaises(ValueError):
            release.execute(self.root, self.output, self.packager)


if __name__ == '__main__':
    unittest.main()
