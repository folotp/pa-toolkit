"""Pinned upstream standards with explicit Claude compatibility and drift detection.

The official skills-ref core validates the parsed Agent Skills metadata. Claude-only
fields are checked separately by the adapter, then explicitly projected out of that
portable core; tool arrays are normalized to the core's space-separated string form.
These conversions are reported and never represented as raw portable conformance.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
from importlib import resources
import re
import urllib.error
import urllib.request

from .source import require, parse_json

CLAUDE_SKILL_FIELDS = frozenset(
    {"argument-hint", "disable-model-invocation", "user-invocable", "model", "context", "agent"}
)
CORE_SKILL_FIELDS = frozenset(
    {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
)


def vendor_text(name):
    """Load package data in editable checkouts or installed wheels; no adjacent repo."""
    return (
        resources.files("pa_devtools").joinpath("vendor").joinpath(name).read_text(encoding="utf-8")
    )


def pins():
    """Return the reviewed standard set; missing or malformed package data fails."""
    value = parse_json(vendor_text("specifications.json"))
    require(
        isinstance(value, dict) and value.get("schema_version") == 1,
        "Invalid specification source inventory",
    )
    require(re.fullmatch(r"[0-9a-f]{40}", value["skills_ref_commit"]), "Invalid skills-ref pin")
    return value


def validate_skill(metadata, directory, profile="claude"):
    """Use the official validator, preserving strict parse/types in the caller.

    Return reported adaptations. The adapter must type-check every declared Claude
    extension before this call. Unknown keys are rejected here too; no catch-all
    removal or validator monkey patch is permitted. Strict portable mode forbids
    both extra fields and tool arrays. skills-ref itself does not check all field
    types, so normative metadata/tool/compatibility constraints are enforced here.
    """
    from skills_ref.validator import validate_metadata

    require(profile in ("claude", "portable"), "Unknown specification profile")
    require(isinstance(metadata, dict), "Skill metadata must be an object")
    allowed = CORE_SKILL_FIELDS | (CLAUDE_SKILL_FIELDS if profile == "claude" else set())
    require(
        set(metadata) <= allowed,
        "Unsupported skill fields: " + ", ".join(sorted(set(metadata) - allowed)),
    )
    for key in ("name", "description"):
        require(
            isinstance(metadata.get(key), str) and metadata[key].strip(),
            f"Skill {key} must be a nonempty string",
        )
    for key in set(metadata) & CLAUDE_SKILL_FIELDS:
        value = metadata[key]
        if key in ("disable-model-invocation", "user-invocable"):
            require(type(value) is bool, f"Claude {key} must be boolean")
        else:
            require(isinstance(value, str) and value.strip(), f"Claude {key} must be text")
            if key == "context":
                require(value == "fork", "Claude context must be fork")
    adapted = sorted(set(metadata) & CLAUDE_SKILL_FIELDS)
    core = {k: v for k, v in metadata.items() if k in CORE_SKILL_FIELDS}
    if "allowed-tools" in core:
        value = core["allowed-tools"]
        if isinstance(value, list) and profile == "claude":
            require(
                all(isinstance(x, str) and x.strip() for x in value),
                "Invalid Claude allowed-tools array",
            )
            core["allowed-tools"] = " ".join(value)
            adapted.append("allowed-tools array -> string")
        require(isinstance(core["allowed-tools"], str), "Portable allowed-tools must be a string")
    if "metadata" in core:
        require(
            isinstance(core["metadata"], dict)
            and all(isinstance(k, str) and isinstance(v, str) for k, v in core["metadata"].items()),
            "Portable metadata must map strings to strings",
        )
    if "license" in core:
        require(
            isinstance(core["license"], str) and core["license"].strip(),
            "Skill license must be a nonempty string",
        )
    if "compatibility" in core:
        require(
            isinstance(core["compatibility"], str) and 1 <= len(core["compatibility"]) <= 500,
            "Skill compatibility must contain 1-500 characters",
        )
    errors = validate_metadata(core, directory)
    require(not errors, "skills-ref: " + "; ".join(errors))
    return adapted


def validate_manifest(manifest, profile="claude"):
    """Validate the official schema, reporting legacy envelope adaptation explicitly.

    In Claude mode the caller owns .claude-plugin/plugin.json and its version. Add
    only the canonical schema identifier to a temporary object for upstream field
    validation. This does not create a portable root manifest or certify package
    portability. Strict mode validates the actual object without injecting fields.
    """
    from jsonschema import Draft202012Validator

    require(profile in ("claude", "portable"), "Unknown specification profile")
    require(isinstance(manifest, dict), "Plugin manifest must be an object")
    schema = parse_json(vendor_text("plugin.schema.json"))
    source = pins()["sources"]["agent-plugins-schema"]
    require(
        hashlib.sha256(vendor_text("plugin.schema.json").encode()).hexdigest() == source["sha256"],
        "Vendored plugin schema differs from reviewed hash",
    )
    Draft202012Validator.check_schema(schema)
    candidate = dict(manifest)
    adapted = []
    if profile == "claude" and "$schema" not in candidate:
        candidate["$schema"] = schema["$id"]
        adapted.append("legacy Claude envelope -> upstream manifest field validation")
    errors = sorted(
        Draft202012Validator(schema).iter_errors(candidate), key=lambda e: str(list(e.path))
    )
    require(not errors, "Agent Plugins schema: " + "; ".join(e.message for e in errors))
    return adapted


def download(url):
    """Fetch reviewed public data only; timeouts/HTTP errors are required failures."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "pa-devtools-specifications/0.1", "Accept": "text/markdown"}
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            content = response.read(2_000_001)
        require(len(content) <= 2_000_000, "Specification source exceeds 2 MB: " + url)
        return content
    except (OSError, urllib.error.URLError) as error:
        raise ValueError(
            f"Upstream specification check unavailable: {url}: {error}. Restore network access and rerun; no latest-spec pass was recorded."
        ) from error


def check_latest(fetch=download):
    """Require reviewed hashes to match current official sources, without executing them.

    Stable publication status is read explicitly: a higher-numbered draft never
    becomes the release target. Any normative/validator/client-contract drift fails
    with a refresh remedy. Downloads are concurrent; every failure is inspected.
    No cached local success receipt substitutes for this online freshness check.
    """
    inventory = pins()
    sources = inventory["sources"]
    failures = []

    def compare(item):
        name, rule = item
        content = fetch(rule["url"])
        if "published_version" in rule:
            match = re.search(
                rb"Agent Plugins Specification ([0-9.]+) is the current published release", content
            )
            require(
                match and match[1].decode() == rule["published_version"],
                "Current published Agent Plugins version changed or cannot be determined",
            )
        else:
            require(
                hashlib.sha256(content).hexdigest() == rule["sha256"],
                f"Upstream drift: {name}; run scripts/dev spec-review, review the source and update its pinned contract/tests",
            )
        return name

    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [(name, pool.submit(compare, (name, rule))) for name, rule in sources.items()]
        for name, task in tasks:
            try:
                task.result()
                print(f"upstream specification: {name} current")
            except (ValueError, OSError) as error:
                failures.append(str(error))
    require(not failures, "\n".join(failures))
    return inventory


def review_sources(fetch=download):
    """Report candidate hashes for human review; never rewrite pins or execute downloads.

    Full-page hashes deliberately fail on editorial changes too. Read the affected
    official page and its supported contract, then update only reviewed inventory
    entries in a normal PR; this report is not a successful freshness attestation.
    """
    result = {}
    for name, rule in pins()["sources"].items():
        content = fetch(rule["url"])
        result[name] = {
            "url": rule["url"],
            "sha256": hashlib.sha256(content).hexdigest(),
            "reviewed_sha256": rule.get("sha256"),
            "bytes": len(content),
        }
    return result
