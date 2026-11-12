"""Resolve official current specifications per run; never reuse a pinned latest-pass.

The reference validator is upstream executable code, installed for this invocation
at the exact freshly resolved official HEAD. It runs without GitHub credentials.
Schemas/prose are downloaded data; repository policy and Claude projections remain
explicit separate checks. Prose retrieval is evidence of source availability, not
machine certification of semantic compliance with natural language.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .source import require, parse_json, frontmatter
from .specifications import download, CLAUDE_SKILL_FIELDS


def revision(repository):
    """Resolve official remote HEAD now; network/ambiguous/non-Git identities fail."""
    require(
        re.fullmatch(r"https://github.com/[\w.-]+/[\w.-]+\.git", repository),
        "Specification repository must be an explicit public GitHub HTTPS URL",
    )
    output = subprocess.check_output(
        ["git", "ls-remote", repository, "HEAD"],
        text=True,
        timeout=45,
    ).splitlines()
    require(
        len(output) == 1 and re.fullmatch(r"[0-9a-f]{40}\s+HEAD", output[0]),
        "Cannot resolve unique official specification HEAD: " + repository,
    )
    return output[0].split()[0]


def raw(repository, sha, path):
    """Build immutable content URLs only after revision resolution."""
    require(not path.startswith("/") and ".." not in Path(path).parts, "Unsafe upstream path")
    return (
        repository.replace("https://github.com/", "https://raw.githubusercontent.com/")[:-4]
        + f"/{sha}/{path}"
    )


def resolve(config, fetch=download, resolve_revision=revision):
    """Resolve published plugin schema, official skills HEAD and current prose sources.

    The publisher's explicit current-published-release statement wins over higher
    working drafts. Editorial prose changes are recorded, not frozen-hash blockers.
    An unrecognized publication/API shape fails instead of guessing a version.
    """
    require(
        type(config.get("schema_version")) is int and config["schema_version"] == 1,
        "Invalid live specification configuration",
    )
    skill_sha = resolve_revision(config["skills_repository"])
    plugin_sha = resolve_revision(config["plugins_repository"])
    sources = {}

    def read(name, url, kind):
        content = fetch(url)
        require(content.strip(), "Empty official specification source: " + url)
        sources[name] = {"url": url, "sha256": hashlib.sha256(content).hexdigest(), "kind": kind}
        return content

    status = read(
        "plugin-publication",
        raw(config["plugins_repository"], plugin_sha, config["plugin_status_path"]),
        "publication-status",
    )
    versions = re.findall(
        rb"Agent Plugins Specification ([0-9]+\.[0-9]+\.[0-9]+) is the current published release",
        status,
    )
    require(
        len(versions) == 1, "Cannot determine the current official published plugin specification"
    )
    version = versions[0].decode()
    schema = parse_json(
        read(
            "plugin-schema",
            raw(
                config["plugins_repository"],
                plugin_sha,
                config["plugin_schema_template"].format(version=version),
            ),
            "official-schema",
        ).decode()
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [
            pool.submit(read, name, url, "prose-only")
            for name, url in config["prose_sources"].items()
        ]
        for task in tasks:
            task.result()
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "skills_ref_commit": skill_sha,
        "plugin_repository_commit": plugin_sha,
        "plugin_version": version,
        "sources": sources,
    }, schema


# Run in uv's isolated latest-validator environment. No repository imports, user
# Python startup hooks, shell interpolation or credentials are needed in that child.
VALIDATE_SKILLS = """
import json,sys
from pathlib import Path
from skills_ref.validator import validate_metadata
items=json.load(open(sys.argv[1],encoding="utf-8"))
errors=[]
for item in items:
    errors.extend(str(item["directory"])+": "+error for error in validate_metadata(item["metadata"],Path(item["directory"])))
if errors:
    raise SystemExit("\\n".join(errors))
print("Latest official skills-ref: "+str(len(items))+" skills passed")
"""


def check(root, report=None):
    """Validate current repository bytes against freshly resolved official contracts.

    Local specs handles raw/Claude types first. Only explicitly supported Claude
    extensions are removed; unknown core fields reach the official validator. The
    returned receipt records provenance; it is never permission to skip a later run.
    No token is passed to newly resolved upstream executable dependencies.
    """
    from jsonschema.validators import validator_for

    root = Path(root)
    if report:
        require(
            not Path(report).resolve().is_relative_to(root.resolve()),
            "Specification receipt must be outside source",
        )
    config = parse_json((root / "config/specifications.json").read_text())
    evidence, schema = resolve(config)
    validator = validator_for(schema, default=None)
    require(
        validator is not None, "Current official schema uses an unsupported JSON Schema dialect"
    )
    validator.check_schema(schema)
    manifest = parse_json((root / config["manifest"]).read_text())
    if config["profile"] == "claude":
        manifest = dict(manifest, **{"$schema": schema["$id"]})
        evidence["adaptations"] = [
            "Legacy Claude manifest: temporary current $schema envelope; portable package layout not certified"
        ]
    errors = list(validator(schema).iter_errors(manifest))
    require(not errors, "Latest official plugin schema: " + "; ".join(e.message for e in errors))
    items = []
    for path in sorted((root / config["skills"]).glob("*/SKILL.md")):
        metadata = frontmatter(path)
        if config["profile"] == "claude":
            metadata = {
                key: value for key, value in metadata.items() if key not in CLAUDE_SKILL_FIELDS
            }
            if isinstance(metadata.get("allowed-tools"), list):
                metadata["allowed-tools"] = " ".join(metadata["allowed-tools"])
        items.append({"directory": str(path.parent), "metadata": metadata})
    require(items, "No skill metadata selected for latest reference validator")
    dependency = (
        "skills-ref @ git+"
        + config["skills_repository"]
        + "@"
        + evidence["skills_ref_commit"]
        + "#subdirectory=skills-ref"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(
            word in key.upper()
            for word in ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "AUTHORIZATION")
        )
        and not key.startswith(("GIT_", "PYTHON"))
    }
    with tempfile.TemporaryDirectory(prefix="pa-official-specs-") as temp:
        payload = Path(temp) / "skills.json"
        payload.write_text(json.dumps(items))
        subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                "--with",
                dependency,
                "python",
                "-I",
                "-c",
                VALIDATE_SKILLS,
                str(payload),
            ],
            cwd=temp,
            env=env,
            check=True,
            timeout=180,
        )
    evidence["results"] = {
        "skills": "PASS",
        "manifest_fields": "PASS",
        "prose_semantics": "MANUAL_REVIEW",
        "marketplace": "NOT_APPLICABLE: this repository has no marketplace manifest",
    }
    print(json.dumps(evidence, indent=2), flush=True)
    if report:
        Path(report).write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence
