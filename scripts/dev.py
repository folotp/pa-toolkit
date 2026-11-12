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
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# Select this checkout's shared engine for launcher Python as well as managed runs.
# Consumers install the same versioned package from a reviewed merged Git SHA.
sys.path.insert(0, str(ROOT / "tools/pa-devtools/src"))
from pa_devtools import source as shared_source
from pa_devtools import planning, snapshots, hooks as shared_hooks
from pa_devtools import specifications

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
    """Delegate the shared source contract; see pa_devtools.source."""
    return shared_source.require(condition, message)


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
    """Delegate the shared source contract; see pa_devtools.source."""
    return shared_source.parse_json(text)


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
    """Delegate the shared source contract; see pa_devtools.source."""
    return shared_source.frontmatter(path)


def text_value(value):
    """True for a nonempty string, excluding implicit YAML booleans/numbers."""
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    """Claude tool declarations support comma/space text or a YAML string array."""
    return text_value(value) or (isinstance(value, list) and all(text_value(v) for v in value))


def specs(profile="claude"):
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
    # Official validators supplement, rather than replace, strict raw YAML/types.
    adaptations = specifications.validate_manifest(manifest, profile)
    for path in skills:
        changes = specifications.validate_skill(frontmatter(path), path.parent, profile)
        if changes:
            print(f"{path.relative_to(ROOT)}: explicit Claude compatibility: {', '.join(changes)}")
    if adaptations:
        print("Manifest profile: " + "; ".join(adaptations))
        print("Portable package layout is not claimed: legacy Claude source remains authoritative.")
    print(
        f"specs: official skills-ref {specifications.pins()['skills_ref_commit']}; "
        f"Agent Plugins {specifications.pins()['agent_plugins_version']}; "
        f"{len(skills)} skills, {len(agents)} agents; profile={profile}"
    )


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
    """Apply the shared Markdown parser to this adapter's selected source/payload."""
    return shared_source.links(source_files() if paths is None else paths, root or ROOT)


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


def development_policy():
    """Load this repository's declarative gates; shared engine owns planning/execution."""
    value = data("config/development.json")
    planning.validate_config(value)
    return value


def run_gate(name):
    """Thin adapter registry: generic engine runs named repository-owned checks."""
    actions = {
        "doctor": doctor,
        "specs": specs,
        "spec-freshness": specifications.check_latest,
        "code": lint,
        "links": links,
        "inventory": inventory,
        "package-contract": package_check,
        "tests": lambda: run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"),
    }
    require(name in actions, "Unknown toolkit gate: " + name)
    actions[name]()


def check():
    """Run all declared gates; commits/main/releases never infer prior local success."""
    policy = development_policy()
    plan = planning.classify(policy, reason="full validation requested")
    planning.execute(ROOT, policy, plan)


def ci_plan(base=None, full=False):
    """Select only affected PR gates after proving a compatible full main baseline."""
    policy = development_policy()
    paths = planning.changed_paths(ROOT, base)
    full = full or (
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
    )
    reason = "full CI requested" if full else None
    if not full and not planning.trusted_github_base(ROOT, base, **policy["baseline"]):
        reason = "no compatible successful full main-push baseline"
    return planning.classify(policy, paths, reason)


def ci(base=None, full=False):
    """Share the planner with humans; keep generic release preflight unconditionally full.

    Full CI invokes the existing generic driver/extension, with one full gate and a
    real archive. Reduced PR CI runs mandatory structural/freshness gates plus affected
    checks. Runtime changes still build/verify the archive using the same package
    command; development-doc-only changes have no changed archive inputs.
    """
    require(not git("status", "--porcelain"), "CI planning/execution requires a clean checkout")
    plan = ci_plan(base, full)
    print(json.dumps(plan, indent=2), flush=True)
    if plan["full"]:
        with tempfile.TemporaryDirectory(prefix="toolkit-ci-release-") as temp:
            run(
                sys.executable,
                str(ROOT / "skills/plugin-release/scripts/release.py"),
                str(ROOT),
                "--dry-run",
                "--output",
                str(Path(temp) / "package"),
                "--result",
                str(Path(temp) / "receipt.json"),
            )
    else:
        planning.execute(ROOT, development_policy(), plan)
        if any(name in package_paths_names() for name in plan["paths"]):
            with tempfile.TemporaryDirectory(prefix="toolkit-ci-package-") as temp:
                package(ROOT / "skills/plugin-release/scripts/package.sh", temp)
        else:
            print("SKIP archive: runtime inventory/bytes unchanged from validated baseline")


def package_paths_names():
    """Expose selected runtime names for impact planning, without an alternate allowlist."""
    return {path.relative_to(ROOT).as_posix() for path in package_paths()}


def check_staged():
    """Apply toolkit branch policy, then the shared actual-index exporter."""
    branch_guard().check_branch(git("branch", "--show-current"))
    snapshots.validate_index(ROOT, ["scripts/dev", "check"])


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
    """Use shared all-destination preflight with toolkit managed-body recognition."""
    events = ("pre-commit", "pre-push")
    shared_hooks.install(
        {e: hook_file(e) for e in events},
        {e: hook_text(e) for e in events},
        lambda event, text: recognized_hook(text, event),
        uninstall,
    )


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
    """Normalize every native edit through the shared, root-explicit contract."""
    return shared_hooks.hook_paths(ROOT, payload)


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
    """Delegate the shared source contract; see pa_devtools.source."""
    return shared_source.parse_version(output)


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
            "import sys, yaml, markdown_it, ruff, jsonschema, skills_ref; print(sys.version.split()[0]); sys.exit(not ((3,11) <= sys.version_info < (3,16)))",
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
            "ci",
            "plan",
            "_gate",
            "spec-freshness",
            "spec-review",
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
    parser.add_argument("--base")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--profile", choices=["claude", "portable"], default="claude")
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
    elif command == "ci":
        ci(args.base, args.full)
    elif command == "plan":
        print(json.dumps(ci_plan(args.base, args.full), indent=2))
    elif command == "_gate":
        require(len(args.extra) == 1, "Use _gate <declared name>")
        run_gate(args.extra[0])
    elif command == "spec-review":
        print(json.dumps(specifications.review_sources(), indent=2))
    elif command == "spec-freshness":
        specifications.check_latest()
    elif command == "format":
        lint(fix=True)
    elif command == "specs":
        specs(args.profile)
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
