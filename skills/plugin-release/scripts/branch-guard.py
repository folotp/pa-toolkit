#!/usr/bin/env python3
"""Install agent-independent main guards without replacing unmanaged hooks."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys

MARKER = '# managed-by: pa-toolkit branch-guard'


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event', choices=['install', 'pre-commit', 'pre-push'])
    args = parser.parse_args()
    if args.event == 'pre-commit':
        if git('branch', '--show-current') in ('', 'main'):
            parser.exit(1, 'Commit on a named feature branch, never main/detached HEAD.\n')
    elif args.event == 'pre-push':
        for line in sys.stdin:
            fields = line.split()
            if len(fields) == 4 and fields[2] == 'refs/heads/main':
                parser.exit(1, 'Direct main push blocked; merge a pull request.\n')
    else:
        for event in ('pre-commit', 'pre-push'):
            path = Path(git('rev-parse', '--path-format=absolute', '--git-path', 'hooks/' + event))
            if path.exists() and MARKER not in path.read_text():
                parser.exit(1, 'Preserving unmanaged hook; integrate manually: ' + str(path) + '\n')
        for event in ('pre-commit', 'pre-push'):
            path = Path(git('rev-parse', '--path-format=absolute', '--git-path', 'hooks/' + event))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('#!/bin/sh\n' + MARKER + '\nexec python3 ' + shlex.quote(str(Path(__file__).resolve())) + ' ' + event + '\n')
            path.chmod(0o755)
            print('Installed ' + str(path))


if __name__ == '__main__':
    main()
