"""Canonical pa-toolkit development policy; no vault, finance or model access.

Generic worktree/index/package patterns are adapted from Organon c5a9cd8.
This repository owns its Claude schemas, runtime inventory and toolchain. No adjacent
checkout is imported. General release orchestration remains in release.py/runbook.md.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MARKER = "# managed-by: pa-toolkit scripts/dev v1"
LEGACY_MARKER = "# managed-by: pa-toolkit branch-guard"
# SemVer prerelease numeric identifiers cannot have leading zeroes; build metadata
# may. Identifiers cannot be empty (including between dots or after a suffix).
SEMVER = (
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def require(condition, message):
    """Fail a required gate with a diagnostic, never silently downgrade it."""
    if not condition:
        raise ValueError(message)


def run(*argv, cwd=None, capture=False, env=None):
    """Execute argv without shell interpolation; propagate required failures."""
    return subprocess.run(
        argv,
        cwd=cwd or ROOT,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    ).stdout


def git(*args):
    """Read Git metadata from the selected checkout, not a primary worktree."""
    return run("git", *args, capture=True).strip()


def data(name):
    """Load required tracked JSON policy; absent/malformed policy fails closed."""
    return parse_json((ROOT / name).read_text())


def parse_json(text):
    """Reject duplicate keys/nonfinite constants instead of hiding invalid config."""

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("Nonfinite JSON constant: " + value)

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def source_files():
    """Include tracked and nonignored new files for precommit development checks.

    Reject missing tracked files through their owning inventory checks; deleted files
    are not lint inputs. Package selection is independently restricted to tracked files.
    """
    names = run("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", capture=True)
    paths = sorted({ROOT / n for n in names.split("\0") if n and (ROOT / n).is_file()})
    for path in paths:
        require(
            path.resolve().is_relative_to(ROOT.resolve()),
            f"External source symlink: {path}; source checks/format must stay in this checkout",
        )
    return paths


def frontmatter(path):
    """Parse safe YAML with duplicate keys rejected, including nested mappings.

    PyYAML's default duplicate-key overwrite would hide a malformed field. Custom
    constructors preserve SafeLoader's rejection of arbitrary Python YAML objects.
    """
    import yaml

    class UniqueLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            require(isinstance(key, str), f"{path}: YAML keys must be strings")
            require(key not in result, f"{path}: duplicate YAML key {key}")
            result[key] = loader.construct_object(value_node, deep=deep)
        return result

    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    text = path.read_text()
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
    require(match, f"{path}: missing YAML frontmatter")
    try:
        result = yaml.load(match[1], Loader=UniqueLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"{path}: invalid YAML: {error}") from error
    require(isinstance(result, dict), f"{path}: frontmatter must be an object")
    require(text[match.end() :].strip(), f"{path}: empty component body")
    return result


def text_value(value):
    """True for a nonempty string, excluding implicit YAML booleans/numbers."""
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    """Claude tool declarations support comma/space text or a YAML string array."""
    return text_value(value) or (isinstance(value, list) and all(text_value(v) for v in value))


def specs():
    """Validate the legacy Claude manifest and explicitly supported component fields.

    Supported fields follow Claude Code, not Organon's portable skills-ref subset.
    Unknown fields require an explicit schema/test/docs decision. Domain semantics and
    skill authoring quality (#14) still require review; this is a structural gate.
    """
    manifest = data(".claude-plugin/plugin.json")
    require(isinstance(manifest, dict), "Claude manifest must be an object")
    require(
        not (ROOT / "plugin.json").exists(), "Version source remains .claude-plugin/plugin.json"
    )
    required = {"name": text_value, "version": text_value, "description": text_value}
    optional = {
        "author": lambda v: isinstance(v, dict)
        and text_value(v.get("name"))
        and set(v) <= {"name", "email", "url"}
        and all(text_value(x) for x in v.values()),
        "keywords": lambda v: isinstance(v, list) and all(text_value(x) for x in v),
        "homepage": text_value,
        "repository": text_value,
        "license": text_value,
    }
    validate_fields(manifest, required, optional, "Claude manifest")
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest["name"]), "Invalid plugin name")
    require(re.fullmatch(SEMVER, manifest["version"]), "Manifest version must be SemVer")
    require(not (ROOT / ".mcp.json").exists(), "Do not bundle a shadow Organon MCP server")
    common = {"name": text_value, "description": text_value}
    skill_fields = {
        "argument-hint": text_value,
        "disable-model-invocation": lambda v: type(v) is bool,
        "user-invocable": lambda v: type(v) is bool,
        "allowed-tools": string_list,
        "model": text_value,
        "context": lambda v: v == "fork",
        "agent": text_value,
        "license": text_value,
        "compatibility": text_value,
        "metadata": lambda v: isinstance(v, dict) and all(text_value(x) for x in v.values()),
    }
    agent_fields = {
        "tools": string_list,
        "disallowedTools": string_list,
        "model": text_value,
        "color": text_value,
        "permissionMode": lambda v: v
        in ("default", "acceptEdits", "dontAsk", "bypassPermissions", "plan", "auto"),
        "maxTurns": lambda v: type(v) is int and v > 0,
        "skills": lambda v: isinstance(v, list) and all(text_value(x) for x in v),
        "memory": lambda v: v in ("user", "project", "local"),
        "background": lambda v: type(v) is bool,
        "isolation": lambda v: v == "worktree",
    }
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    agents = sorted((ROOT / "agents").glob("*.md"))
    require(skills and agents, "Skills and agents must be present")
    for path in skills + agents:
        values = frontmatter(path)
        is_skill = path.name == "SKILL.md"
        validate_fields(values, common, skill_fields if is_skill else agent_fields, str(path))
        expected = path.parent.name if is_skill else path.stem
        require(
            values["name"] == expected
            and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", expected)
            and len(expected) <= 64,
            f"{path}: name must match its path (kebab-case, <=64)",
        )
        require(
            len(values["description"]) <= (1024 if is_skill else 4096),
            f"{path}: description exceeds the supported limit",
        )
        require(
            "<" not in values["description"] and ">" not in values["description"],
            f"{path}: description must not contain XML delimiters",
        )
    release_skill = frontmatter(ROOT / "skills/plugin-release/SKILL.md")
    require(
        release_skill.get("disable-model-invocation") is True, "Release skill must stay user-only"
    )
    gatekeeper = frontmatter(ROOT / "agents/decision-gatekeeper.md")
    require("tools" not in gatekeeper, "Gatekeeper tools must remain surface-neutral")
    print(f"specs: {len(skills)} skills, {len(agents)} agents; legacy Claude manifest")


def validate_fields(values, required, optional, label):
    """Enforce field presence, types and an explicit extension boundary."""
    require(
        set(values) <= required.keys() | optional.keys(),
        f"{label}: unsupported fields {set(values) - required.keys() - optional.keys()}",
    )
    for key, predicate in required.items():
        require(key in values and predicate(values[key]), f"{label}: invalid/missing {key}")
    for key, predicate in optional.items():
        require(key not in values or predicate(values[key]), f"{label}: invalid {key}")


def links(paths=None, root=None):
    """Parse Markdown links/images/reference links; skip examples, URLs and vault links.

    Check relative file existence and repository containment, not network availability
    or heading anchors. The same parser verifies shipped runtime resource links.
    """
    from markdown_it import MarkdownIt

    root = (root or ROOT).resolve()
    parser = MarkdownIt()
    errors = []
    for path in paths if paths is not None else source_files():
        if path.suffix != ".md":
            continue
        for token in parser.parse(path.read_text()):
            for child in token.children or []:
                target = (
                    child.attrGet("href")
                    if child.type == "link_open"
                    else child.attrGet("src")
                    if child.type == "image"
                    else None
                )
                if not target or target.startswith(("#", "[")) or urlsplit(target).scheme:
                    continue
                dest = unquote(urlsplit(target).path)
                resolved = (path.parent / dest).resolve()
                if dest and (not resolved.is_relative_to(root) or not resolved.exists()):
                    errors.append(
                        f"{path.resolve().relative_to(root)}: missing/outside link {target}"
                    )
    require(not errors, "\n".join(errors))
    print("links: passed (relative files; excludes external URLs, vault links and anchors)")


def inventory():
    """Require exact current README component coverage; no invented release history."""
    text = (ROOT / "README.md").read_text().split("## Install", 1)[0]
    actual_skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    listed_skills = set(re.findall(r"^\| `([a-z0-9-]+)` \|", text, re.M))
    actual_agents = {p.stem for p in (ROOT / "agents").glob("*.md")}
    listed_agents = set(re.findall(r"^- \*\*`([a-z0-9-]+)`\*\*", text, re.M))
    require(
        actual_skills == listed_skills,
        f"README skill inventory differs: {actual_skills ^ listed_skills}",
    )
    require(
        actual_agents == listed_agents,
        f"README agent inventory differs: {actual_agents ^ listed_agents}",
    )
    require(
        (ROOT / "CLAUDE.md").read_text().strip() == "@AGENTS.md",
        "CLAUDE.md must import the canonical contract only",
    )
    print("inventory: passed")


def shell_files():
    """Select shell code including the extensionless shared launcher."""
    return [str(p) for p in source_files() if p.suffix == ".sh" or p == ROOT / "scripts/dev"]


def lint(fix=False):
    """Validate all Python/shell/CI sources. Only explicit format writes source."""
    shells = shell_files()
    python = [str(p) for p in source_files() if p.suffix == ".py"]
    if shells:
        run("shfmt", "-i", "4", "-ci", "-w" if fix else "-d", *shells)
    if python:
        run(sys.executable, "-m", "ruff", "format", *([] if fix else ["--check"]), *python)
    if fix:
        return
    for name in shells:
        run("bash", "-n", name)
    if shells:
        run("shellcheck", "-x", "--severity=warning", *shells)
    for name in python:
        ast.parse(Path(name).read_text(), filename=name)
    if python:
        run(sys.executable, "-m", "ruff", "check", *python)
    for path in source_files():
        if path.suffix == ".json":
            parse_json(path.read_text())
    workflows = [
        str(p)
        for p in source_files()
        if p.parent == ROOT / ".github/workflows" and p.suffix in (".yml", ".yaml")
    ]
    if workflows:
        run("actionlint", *workflows)
    run("git", "diff", "--check")
    run("git", "diff", "--cached", "--check")


def package_paths():
    """Select explicit tracked regular runtime files; never glob local skill clutter.

    The reviewed allowlist is exact, sorted-independent and duplicate-free. Runtime
    symlinks are not needed here and rejected instead of dereferencing private data.
    """
    names = data("config/package-files.json")
    require(
        isinstance(names, list) and names and all(text_value(n) for n in names),
        "Package inventory must be a nonempty string array",
    )
    require(len(names) == len(set(names)), "Duplicate package input")
    tracked = set(run("git", "ls-files", "-z", capture=True).split("\0"))
    forbidden = {
        ".git",
        ".claude",
        ".codex",
        ".agents",
        ".venv",
        "__pycache__",
        "tests",
        "config",
        "dist",
        "build",
        "docs",
        ".github",
    }
    paths = []
    for name in names:
        path = Path(name)
        require(
            not path.is_absolute() and ".." not in path.parts and path.as_posix() == name,
            f"Unsafe package input: {name}",
        )
        require(
            not forbidden.intersection(path.parts)
            and path.suffix not in (".pyc", ".bak", ".plugin", ".skill")
            and path.name not in (".DS_Store", ".env"),
            f"Development/local input in package: {name}",
        )
        source = ROOT / path
        require(
            source.resolve().is_relative_to(ROOT.resolve()) and not source.is_symlink(),
            f"External/symlink package input: {name}",
        )
        require(
            name in tracked and source.is_file(),
            f"Package input missing or untracked: {name}; stage and review it",
        )
        paths.append(source)
    return sorted(paths)


def package_check():
    """Require all runtime components/resources and check their staged link closure."""
    paths = package_paths()
    names = {p.relative_to(ROOT).as_posix() for p in paths}
    required = {".claude-plugin/plugin.json", "README.md", "AGENTS.md"}
    required |= {p.relative_to(ROOT).as_posix() for p in (ROOT / "skills").glob("*/SKILL.md")}
    required |= {p.relative_to(ROOT).as_posix() for p in (ROOT / "agents").glob("*.md")}
    required |= {
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "skills/plugin-release").rglob("*")
        if p.is_file() and p in source_files()
    }
    require(required <= names, f"Runtime inventory missing: {required - names}")
    with tempfile.TemporaryDirectory(prefix="toolkit-package-contract-") as temp:
        stage = Path(temp)
        stage_files(paths, stage)
        links(list(stage.rglob("*.md")), stage)
    print(f"package contract: {len(paths)} explicit tracked runtime files")


def stage_files(paths, stage):
    """Copy selected regular source bytes and executable bits into private staging."""
    for path in paths:
        target = stage / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def package(packager, output):
    """Delegate ZIP construction; verify exact inventory, integrity and source bytes.

    Only copy a verified archive to an explicit destination outside the source tree.
    Does not run heavy gates again: release preflight owns the full check for this
    invocation. Direct users must run check before treating the archive as releasable.
    """
    output = Path(output).expanduser().resolve()
    require(not output.is_relative_to(ROOT.resolve()), "Package output must be outside source")
    packager = Path(packager).expanduser().resolve()
    require(packager.is_file(), "Pass an existing --packager package.sh")
    package_check()
    with tempfile.TemporaryDirectory(prefix="toolkit-package-") as temp:
        stage = Path(temp)
        paths = package_paths()
        stage_files(paths, stage)
        run("bash", str(packager), str(stage))
        manifest = data(".claude-plugin/plugin.json")
        built = stage / f"{manifest['name']}-v{manifest['version']}.plugin"
        with zipfile.ZipFile(built) as archive:
            require(archive.testzip() is None, "Corrupt runtime archive")
            files = [n for n in archive.namelist() if not n.endswith("/")]
            expected = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in paths}
            require(
                len(files) == len(set(files)) and set(files) == expected.keys(),
                "Archive differs from runtime inventory",
            )
            for name, content in expected.items():
                require(archive.read(name) == content, f"Archive bytes differ: {name}")
        output.mkdir(parents=True, exist_ok=True)
        destination = output / built.name
        shutil.copy2(built, destination)
        print(destination)


def check():
    """One complete mandatory gate for humans, agents, staged snapshots, CI, release."""
    doctor()
    specs()
    lint()
    links()
    inventory()
    package_check()
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")


def check_staged():
    """Export the real index into a new Git repository; never read unstaged repairs.

    Inherited GIT_* variables must not reconnect the temporary repository to the
    caller's index/worktree. checkout-index preserves staged modes and deletions.
    The temporary index is reset to the exported tree so file discovery sees additions.
    """
    branch_guard().check_branch(git("branch", "--show-current"))
    tree = git("write-tree")  # Unmerged index fails before any export.
    with tempfile.TemporaryDirectory(prefix="toolkit-index-") as temp:
        run("git", "checkout-index", "--all", "--prefix", temp + os.sep)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

        def isolated(*args):
            run(*args, cwd=temp, env=env)

        isolated("git", "init", "-q", "-b", "chore/index-snapshot")
        isolated("git", "fetch", "-q", str(ROOT), "HEAD")
        isolated("git", "update-ref", "HEAD", "FETCH_HEAD")
        # Import staged tree objects (including new blobs) through a temporary index
        # only in the source repository; no branch or real index is changed.
        objects = git("rev-parse", "--path-format=absolute", "--git-path", "objects")
        alternate = Path(temp) / ".git/objects/info/alternates"
        alternate.write_text(objects + "\n")
        isolated("git", "read-tree", tree)
        launcher = Path(temp) / "scripts/dev"
        require(launcher.is_file(), "Staged scripts/dev missing; update the branch")
        isolated(str(launcher), "check")


def hook_file(event):
    """Ask Git for shared/custom hook paths, including relative core.hooksPath."""
    # --path-format=absolute canonicalizes a final hook symlink on some Git builds.
    # Preserve that final path so the installer can refuse symlink replacement.
    path = Path(git("rev-parse", "--git-path", "hooks/" + event))
    return path if path.is_absolute() else ROOT / path


def recognized_hook(text, event):
    """Accept only exact generated launchers, never a marker in arbitrary user code."""
    if text == hook_text(event):
        return True
    # Compare the complete previously generated body, including shell quoting.
    # A marker copied into an unmanaged hook never authorizes discarding its code.
    lines = text.splitlines()
    if len(lines) != 3 or lines[:2] != ["#!/bin/sh", LEGACY_MARKER]:
        return False
    try:
        argv = shlex.split(lines[2])
    except ValueError:
        return False
    if len(argv) != 4 or argv[:2] != ["exec", "python3"] or argv[3] != event:
        return False
    script = Path(argv[2])
    return (
        script.is_absolute()
        and script.name == "branch-guard.py"
        and text
        == (
            "#!/bin/sh\n"
            + LEGACY_MARKER
            + "\nexec python3 "
            + shlex.quote(str(script))
            + " "
            + event
            + "\n"
        )
    )


def hook_text(event):
    """Resolve the active checkout at event time; fail clearly on older branches."""
    command = "check-staged" if event == "pre-commit" else "pre-push"
    return (
        "#!/bin/sh\n" + MARKER + "\nset -eu\n"
        'root="$(git rev-parse --show-toplevel)"\n'
        'if [ ! -x "$root/scripts/dev" ]; then\n'
        '    echo "Shared checks missing in this worktree; update branch or restore hooks per docs/development.md." >&2\n'
        '    exit 1\nfi\nexec "$root/scripts/dev" ' + command + "\n"
    )


def install_hooks(uninstall=False):
    """Preflight both destinations before writing; preserve all unmanaged hooks.

    Replacing a recognized old guard upgrades its precommit behavior and retains
    destination protection. Shared hooks affect all worktrees. Uninstall removes
    only exact current launchers, never legacy/unmanaged hooks or hook symlinks.
    """
    paths = {event: hook_file(event) for event in ("pre-commit", "pre-push")}
    for event, path in paths.items():
        require(not path.is_symlink(), f"Preserving unmanaged hook symlink: {path}")
        if path.exists():
            accepted = (
                path.read_text() == hook_text(event)
                if uninstall
                else recognized_hook(path.read_text(), event)
            )
            require(
                accepted,
                f"Preserving unmanaged hook: {path}; compose manually per docs/development.md",
            )
    for event, path in paths.items():
        if uninstall:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(hook_text(event))
            path.chmod(0o755)
        print(f"{'Removed' if uninstall else 'Installed'} {path}")


def branch_guard():
    """Load the distributed generic guard so branch policy has one implementation."""
    import types

    path = ROOT / "skills/plugin-release/scripts/branch-guard.py"
    # Executing trusted source directly avoids writing __pycache__ into a checkout
    # during lightweight hooks or staged export, without changing global Python flags.
    guard = types.ModuleType("toolkit_branch_guard")
    guard.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), guard.__dict__)

    return guard


def pre_push(stream):
    """Reuse the generic main-destination policy; no second branch policy copy."""
    branch_guard().check_push(stream)


def hook_paths(payload):
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
    cwd_value = payload.get("cwd", str(ROOT))
    require(text_value(cwd_value), "Hook cwd must be an absolute path string")
    cwd = Path(cwd_value)
    require(cwd.is_absolute(), "Hook cwd must be absolute")
    paths = []
    for name in names:
        require(text_value(name), "Invalid edit path")
        path = (cwd / name).resolve()
        require(path.is_relative_to(ROOT.resolve()), f"Edit path outside repository: {path}")
        paths.append(path)
    return list(dict.fromkeys(paths))


def advisory(argv):
    """Bound tool output and report empty nonzero failures; never claim a skipped pass."""
    result = subprocess.run(
        argv, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return result.stdout[-3000:] or (
        "passed"
        if result.returncode == 0
        else f"failed without diagnostic output (exit {result.returncode})"
    )


def hook(event):
    """Thin lifecycle output contract; advisories never format or continue Stop.

    Lightweight launcher Python avoids environment downloads on every edit. Python
    syntax/JSON checks and external shell tools give feedback; full schemas/links/
    regressions remain in the mandatory Git/CI gate. Each message is <=4000 chars.
    """
    payload = json.load(sys.stdin)
    require(isinstance(payload, dict), "Hook payload must be an object")
    if event == "start":
        message = f"pa-toolkit development: {ROOT}; branch {git('branch', '--show-current') or 'DETACHED'}. Read AGENTS.md; scripts/dev check is the required gate. Use a named feature worktree before committing."
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": message,
                    }
                }
            )
        )
        return
    if event == "stop":
        if payload.get("stop_hook_active"):
            return
        files = shell_files()
        message = (
            advisory(["shellcheck", "-x", "--severity=warning", *files])
            if files
            else "No shell sources"
        )
        print(
            json.dumps(
                {
                    "systemMessage": "pa-toolkit Stop lint (advisory; files unchanged): "
                    + message[:3500]
                }
            )
        )
        return
    paths = hook_paths(payload)
    if event == "edit":
        # The repository rule is branch/worktree isolation, not immutable content.
        branch_guard().check_branch(git("branch", "--show-current"), action="edit")
        return
    feedback = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            if path.suffix == ".py":
                ast.parse(path.read_text(), filename=str(path))
            elif path.suffix == ".json":
                parse_json(path.read_text())
            elif path.suffix == ".sh" or path == ROOT / "scripts/dev":
                feedback.append("shfmt: " + advisory(["shfmt", "-i", "4", "-ci", "-d", str(path)]))
                feedback.append(
                    "ShellCheck: " + advisory(["shellcheck", "-x", "--severity=warning", str(path)])
                )
        except (ValueError, SyntaxError, OSError) as error:
            feedback.append(str(error))
    message = (
        "pa-toolkit edit feedback (advisory; files unchanged; run scripts/dev format explicitly): "
        + (
            "\n".join(feedback)
            or "structural edit accepted; run scripts/dev check for the full gate"
        )
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": message[:4000],
                }
            }
        )
    )


def parse_version(output):
    """Normalize vendor tool banners; unknown formats must fail diagnostics."""
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", output)
    require(match, "Cannot parse tool version: " + output[:160])
    return tuple(int(x or 0) for x in match.groups())


def doctor():
    """Diagnose launcher separately from managed Python and locked imports.

    No global settings are changed. Locked sync/cache/network failures carry a setup
    remedy and are required failures. Claude/Codex are optional session clients only.
    """
    require(sys.version_info >= (3, 9), "Launcher Python 3.9+ required on PATH")
    failures = []
    policy = data("config/toolchain.json")
    require(isinstance(policy, dict) and policy, "Malformed toolchain policy")
    for name, rule in policy.items():
        require(
            isinstance(rule, dict)
            and set(rule) == {"minimum", "flag"}
            and all(text_value(v) for v in rule.values()),
            f"Invalid toolchain rule: {name}",
        )
        found = shutil.which(name)
        if not found:
            failures.append(f"Install {name} >= {rule['minimum']}; see docs/development.md")
            print(f"{name}: MISSING")
            continue
        result = subprocess.run(
            [found, rule["flag"]], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        try:
            version = parse_version(result.stdout)
            print(f"{name}: {'.'.join(map(str, version))} ({found})")
            require(
                result.returncode == 0 and version >= parse_version(rule["minimum"]),
                f"{name} >= {rule['minimum']} required; upgrade the detected executable",
            )
        except ValueError as error:
            failures.append(str(error))
    print(
        f"Executing Python: {sys.version.split()[0]} ({sys.executable}); launcher needs 3.9+, managed project needs 3.11-3.15"
    )
    try:
        managed = run(
            "uv",
            "run",
            "--locked",
            "--project",
            str(ROOT),
            "python",
            "-c",
            "import sys, yaml, markdown_it, ruff; print(sys.version.split()[0]); sys.exit(not ((3,11) <= sys.version_info < (3,16)))",
            capture=True,
        )
        print("Managed project Python/imports: " + managed.strip())
    except (OSError, subprocess.CalledProcessError):
        failures.append(
            "Managed environment unavailable: run uv sync --locked with approved network/cache access; see docs/development.md"
        )
    for event in ("pre-commit", "pre-push"):
        path = hook_file(event)
        state = (
            "current"
            if path.is_file() and path.read_text() == hook_text(event)
            else "missing/legacy/unmanaged (run install-hooks after review)"
        )
        print(f"{event}: {path} ({state})")
    require(not failures, "; ".join(failures))


def main():
    """Dispatch common gates; keep client output JSON and CLI failures actionable."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "doctor",
            "check",
            "check-staged",
            "format",
            "specs",
            "links",
            "inventory",
            "package-check",
            "package",
            "release-check",
            "install-hooks",
            "pre-push",
            "worktree",
            "hook",
        ],
    )
    parser.add_argument("extra", nargs="*")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument(
        "--packager", default=str(ROOT / "skills/plugin-release/scripts/package.sh")
    )
    parser.add_argument("--output")
    args = parser.parse_args()
    command = args.command
    if command == "hook":
        require(
            args.extra in (["start"], ["edit"], ["feedback"], ["stop"]),
            "Use hook start|edit|feedback|stop",
        )
        try:
            hook(args.extra[0])
        except (ValueError, OSError, SyntaxError, subprocess.CalledProcessError) as error:
            if args.extra[0] in ("stop", "feedback"):
                print(
                    json.dumps(
                        {"systemMessage": "pa-toolkit advisory unavailable: " + str(error)[:2000]}
                    )
                )
            else:
                raise
        return
    if command == "doctor":
        doctor()
    elif command == "check-staged" or (command == "check" and args.staged):
        check_staged()
    elif command == "check":
        check()
    elif command == "format":
        lint(fix=True)
    elif command == "specs":
        specs()
    elif command == "links":
        links()
    elif command == "inventory":
        inventory()
    elif command == "package-check":
        package_check()
    elif command == "package":
        require(args.output, "--output is required (outside source)")
        package(args.packager, args.output)
    elif command == "release-check":
        require(not git("status", "--porcelain"), "Release preflight requires a clean tree")
        check()  # One heavy gate; the extension package command builds the real ZIP.
    elif command == "install-hooks":
        install_hooks(args.uninstall)
    elif command == "pre-push":
        pre_push(sys.stdin)
    elif command == "worktree":
        require(len(args.extra) == 2, "Usage: scripts/dev worktree <branch> <destination>")
        require(
            re.fullmatch(r"(feat|fix|chore|perf|docs)/.+", args.extra[0]),
            "Use a documented branch prefix",
        )
        run(
            "git",
            "worktree",
            "add",
            "-b",
            args.extra[0],
            str(Path(args.extra[1]).expanduser().resolve()),
            "main",
        )
    print(f"{command}: passed")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, SyntaxError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(2 if len(sys.argv) > 1 and sys.argv[1] == "hook" else 1)
