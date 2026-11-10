"""Exercise release contracts in disposable fixtures; never publish or use a vault."""
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('guard', Path(__file__).resolve().parents[1] / 'skills/plugin-release/scripts/branch-guard.py')
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class GuardTests(unittest.TestCase):
    def test_main_and_detached_commits_denied(self):
        for branch in ('main', ''):
            with patch('sys.argv', ['guard', 'pre-commit']), patch.object(guard, 'git', return_value=branch), self.assertRaises(SystemExit):
                guard.main()

    def test_feature_commit_allowed(self):
        with patch('sys.argv', ['guard', 'pre-commit']), patch.object(guard, 'git', return_value='chore/example'):
            guard.main()

    def test_push_checks_destination_even_from_feature(self):
        for destination, denied in [('main', True), ('chore/example', False)]:
            with patch('sys.argv', ['guard', 'pre-push']), patch('sys.stdin', io.StringIO('refs/heads/chore/a abc refs/heads/' + destination + ' def\n')):
                if denied:
                    with self.assertRaises(SystemExit):
                        guard.main()
                else:
                    guard.main()
