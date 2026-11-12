"""Shared source contracts; optional parser dependencies are imported lazily.

Launcher/index/hook operations require only Python 3.9 stdlib. Full checks install
pa-devtools[checks] in the managed environment. No module reads an adjacent checkout.
"""

from __future__ import annotations

import json
import re
from urllib.parse import unquote, urlsplit


def require(condition, message):
    """Fail a required gate with a diagnostic, never silently downgrade it."""
    if not condition:
        raise ValueError(message)


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


def parse_version(output):
    """Normalize vendor tool banners; unknown formats must fail diagnostics."""
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", output)
    require(match, "Cannot parse tool version: " + output[:160])
    return tuple(int(x or 0) for x in match.groups())


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


def links(paths, root):
    """Parse Markdown links/images/reference links; skip examples, URLs and vault links.

    Check relative file existence and repository containment, not network availability
    or heading anchors. The same parser verifies shipped runtime resource links.
    """
    from markdown_it import MarkdownIt

    root = root.resolve()
    parser = MarkdownIt()
    errors = []
    for path in paths:
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
