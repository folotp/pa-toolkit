"""Shared native edit normalization and all-destination hook installation."""

from pathlib import Path
import re

from .source import require


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
            content = path.read_text()
            accepted = content == bodies[event] if uninstall else recognized(event, content)
            require(
                accepted,
                f"Preserving unmanaged hook: {path}; compose manually per docs/development.md",
            )
    for event, path in paths.items():
        if uninstall:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(bodies[event])
            path.chmod(0o755)
        print(f"{'Removed' if uninstall else 'Installed'} {path}")
