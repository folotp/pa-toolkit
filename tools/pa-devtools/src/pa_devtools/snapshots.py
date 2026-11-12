"""Export the actual Git index for independent full validation in any repository."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from .source import require


def validate_index(root, command):
    """Run argv inside an isolated index snapshot, preserving the caller's tree.

    The adapter checks its branch policy before calling. Git reads staged bytes/modes,
    not unstaged repairs; unmerged indexes fail write-tree. An object alternate makes
    newly staged blobs available without copying or modifying the original index.
    Strip inherited GIT_* only for isolated subprocesses, including GIT_INDEX_FILE.
    """
    root = Path(root)

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    tree = git("write-tree")
    with tempfile.TemporaryDirectory(prefix="pa-dev-index-") as temp:
        subprocess.run(
            ["git", "checkout-index", "--all", "--prefix", temp + os.sep], cwd=root, check=True
        )
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

        def isolated(*argv):
            subprocess.run(argv, cwd=temp, env=env, check=True)

        isolated("git", "init", "-q", "-b", "chore/index-snapshot")
        isolated("git", "fetch", "-q", str(root), "HEAD")
        isolated("git", "update-ref", "HEAD", "FETCH_HEAD")
        alternate = Path(temp) / ".git/objects/info/alternates"
        alternate.write_text(
            git("rev-parse", "--path-format=absolute", "--git-path", "objects") + "\n"
        )
        isolated("git", "read-tree", tree)
        argv = list(command)
        require(
            argv and all(isinstance(x, str) and x for x in argv),
            "Snapshot command requires nonempty argv",
        )
        executable = Path(temp) / argv[0]
        require(executable.is_file(), "Staged validation launcher missing; update the branch")
        argv[0] = str(executable)
        isolated(*argv)
