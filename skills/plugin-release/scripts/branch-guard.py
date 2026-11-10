#!/usr/bin/env python3
"""Install agent-independent main guards without replacing unmanaged hooks."""

import argparse
from pathlib import Path
import shlex
import subprocess
import sys

MARKER = "# managed-by: pa-toolkit branch-guard"


def git(*args):
    """Read Git metadata in the invoking repository, not the driver’s own checkout."""
    return subprocess.check_output(["git", *args], text=True).strip()


def check_branch(branch, action="commit"):
    """One named-feature policy shared by generic Git and toolkit lifecycle guards."""
    if branch in ("", "main"):
        raise ValueError(
            f"Use a named feature worktree to {action}; main/detached HEAD is blocked."
        )


def check_push(stream):
    """Reject a main destination in Git's four-field pre-push input.

    Shared by this generic guard and the toolkit development adapter. Malformed
    records fail closed instead of accidentally permitting an uninspected update.
    """
    for line in stream:
        fields = line.split()
        if len(fields) != 4:
            raise ValueError("Malformed pre-push update; expected four Git fields")
        if fields[2] == "refs/heads/main":
            raise ValueError("Direct main push blocked; merge a pull request.")


def main():
    """Install managed launchers or enforce Git’s pre-commit/pre-push contracts.

    pre-commit rejects main/detached HEAD. pre-push reads Git’s four-field ref updates
    from stdin and checks the remote destination, even when pushing a feature HEAD.
    Installation resolves shared/custom hooks paths and checks both destinations
    before writing either file; any unmanaged hook requires manual integration.
    Launchers retain this script’s absolute path: reinstall before removing or moving
    the source checkout. Server-side branch protection is the independent merge gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", choices=["install", "pre-commit", "pre-push"])
    args = parser.parse_args()
    if args.event == "pre-commit":
        try:
            check_branch(git("branch", "--show-current"))
        except ValueError as error:
            parser.exit(1, str(error) + "\n")
    elif args.event == "pre-push":
        try:
            check_push(sys.stdin)
        except ValueError as error:
            parser.exit(1, str(error) + "\n")
    else:
        # Preflight every destination before mutating the shared hooks directory.
        for event in ("pre-commit", "pre-push"):
            path = Path(git("rev-parse", "--path-format=absolute", "--git-path", "hooks/" + event))
            if path.exists() and MARKER not in path.read_text():
                parser.exit(1, "Preserving unmanaged hook; integrate manually: " + str(path) + "\n")
        for event in ("pre-commit", "pre-push"):
            path = Path(git("rev-parse", "--path-format=absolute", "--git-path", "hooks/" + event))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "#!/bin/sh\n"
                + MARKER
                + "\nexec python3 "
                + shlex.quote(str(Path(__file__).resolve()))
                + " "
                + event
                + "\n"
            )
            path.chmod(0o755)
            print("Installed " + str(path))


if __name__ == "__main__":
    main()
