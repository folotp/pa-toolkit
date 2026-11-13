"""Shared native edit normalization and all-destination hook installation."""

import fcntl
import json
import os
from pathlib import Path
import stat
import re

from .source import require


EDIT_TOOLS = frozenset(("apply_patch", "Write", "Edit", "MultiEdit"))


def hook_paths(root, payload):
    """Normalize Claude file edits and every Codex add/update/delete/move header.

    Resolve cwd and symlinks; reject malformed payloads or outside-repository edits.
    There is no toolkit protected-reference list or implicit edit authorization.
    """
    require(isinstance(payload, dict), "Hook payload must be an object")
    inputs = payload.get("tool_input")
    require(isinstance(inputs, dict), "Unsupported tool_input shape")
    if payload.get("tool_name") == "apply_patch":
        command = inputs.get("command")
        require(
            isinstance(command, str)
            and command.startswith("*** Begin Patch\n")
            and command.rstrip().endswith("*** End Patch"),
            "Malformed apply_patch payload",
        )
        names = re.findall(
            r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", command, re.M
        )
        require(names, "Patch has no supported file headers")
    elif payload.get("tool_name") in ("Write", "Edit", "MultiEdit"):
        names = [inputs.get("file_path")]
    else:
        raise ValueError("Unsupported edit payload; use Git/CI for other editing paths")
    cwd_value = payload.get("cwd", str(root))
    require(
        isinstance(cwd_value, str) and cwd_value.strip(), "Hook cwd must be an absolute path string"
    )
    cwd = Path(cwd_value)
    require(cwd.is_absolute(), "Hook cwd must be absolute")
    paths = []
    for name in names:
        require(isinstance(name, str) and name.strip(), "Invalid edit path")
        path = (cwd / name).resolve()
        require(path.is_relative_to(root.resolve()), f"Edit path outside repository: {path}")
        paths.append(path)
    return list(dict.fromkeys(paths))


def install(paths, bodies, recognized, uninstall=False):
    """Preflight every destination before writing; never replace unmanaged hooks.

    paths/bodies are adapter-selected event maps; recognized(event, text) authorizes
    only known generated versions. Removal accepts only exact current bodies.
    Preserve final symlinks even when their targets happen to look managed.
    """
    require(paths.keys() == bodies.keys(), "Hook paths/bodies must cover the same events")
    for event, path in paths.items():
        require(not path.is_symlink(), f"Preserving unmanaged hook symlink: {path}")
        if path.exists():
            require(
                path.is_file(),
                f"Hook destination is not a regular file: {path}; move it manually before retrying",
            )
            try:
                content = path.read_text()
            except OSError as error:
                raise ValueError(
                    f"Cannot read hook destination {path}; check ownership/permissions before retrying"
                ) from error
            accepted = content == bodies[event] if uninstall else recognized(event, content)
            require(
                accepted,
                f"Preserving unmanaged hook: {path}; compose manually per docs/development.md",
            )
    for event, path in paths.items():
        try:
            if uninstall:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(bodies[event])
                path.chmod(0o755)
        except OSError as error:
            raise ValueError(
                f"Cannot {'remove' if uninstall else 'install'} hook {path}; check destination ownership/permissions and core.hooksPath; inspect both hooks before retrying (writes may be partial)"
            ) from error
        print(f"{'Removed' if uninstall else 'Installed'} {path}")


def append_receipt(root, destination, record):
    """Append one receipt to an opt-in, existing private file outside the checkout.

    Unix (supported macOS/Linux) append/lock semantics serialize concurrent writers.
    No directories/files are created, symlinks are refused, and no payload, path,
    diagnostic, prompt or configuration is recorded. Errors belong to the advisory
    caller; recording must never override the lifecycle's enforcement outcome.
    """
    path = Path(destination)
    require(path.is_absolute(), "Receipt path must be absolute")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        # Python 3.9-3.12 use RuntimeError for a symlink loop; newer launchers
        # use OSError. Strict resolution also refuses unresolved loops on every
        # supported version. Observation must not replace the hook outcome.
        raise ValueError("Receipt path cannot be resolved") from error
    require(not resolved.is_relative_to(root.resolve()), "Receipt must stay outside source")
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and info.st_mode & 0o077 == 0
            and info.st_nlink == 1,
            "Receipt must be a private regular file owned by this user",
        )
        value = (json.dumps(record, separators=(",", ":")) + "\n").encode()
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            require(os.write(descriptor, value) == len(value), "Incomplete receipt write")
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)
