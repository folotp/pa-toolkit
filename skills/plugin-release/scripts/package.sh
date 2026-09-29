#!/usr/bin/env bash
# package.sh — build the <name>-v<version>.plugin archive at a plugin repo's root.
#
# The .plugin archive is a zip of the plugin tree minus build/eval/git noise.
# Distribution is via GitHub Release asset (the .plugin is gitignored).
#
# Usage:
#   bash package.sh [<repo-root>]         # build at repo root (default: git toplevel of cwd)
#   bash package.sh [<repo-root>] --dry   # list contents only
#
# Reads name and version from <repo-root>/.claude-plugin/plugin.json.

set -euo pipefail

REPO_ROOT=""
DRY=0
for arg in "$@"; do
    case "$arg" in
        --dry) DRY=1 ;;
        -h|--help)
            sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        -*)
            echo "error: unknown flag: $arg" >&2
            exit 2
            ;;
        *) REPO_ROOT="$arg" ;;
    esac
done

if [[ -z "$REPO_ROOT" ]]; then
    REPO_ROOT="$(git rev-parse --show-toplevel)"
fi
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
MANIFEST="${REPO_ROOT}/.claude-plugin/plugin.json"

require_tool() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "error: required tool not on PATH: $1" >&2
        exit 2
    }
}
require_tool jq
require_tool zip

[[ -f "$MANIFEST" ]] || { echo "error: $MANIFEST not found" >&2; exit 2; }

NAME="$(jq -r '.name' "$MANIFEST")"
VERSION="$(jq -r '.version' "$MANIFEST")"
[[ -n "$NAME" && "$NAME" != "null" ]] || { echo "error: .name missing from $MANIFEST" >&2; exit 2; }
[[ -n "$VERSION" && "$VERSION" != "null" ]] || { echo "error: .version missing from $MANIFEST" >&2; exit 2; }

ARCHIVE="${REPO_ROOT}/${NAME}-v${VERSION}.plugin"

cd "$REPO_ROOT"

# Excluded from the archive — keep in sync with .gitignore intent.
EXCLUDES=(
    '.git/*'
    '.git/**/*'
    'eval-workspace/*'
    'eval-workspace/**/*'
    'eval-workspace-*/*'
    'eval-workspace-*/**/*'
    'evals/iteration-*/*'
    'evals/iteration-*/**/*'
    '*.plugin'
    '*.skill'
    '__pycache__/*'
    '**/__pycache__/*'
    '*.pyc'
    '.DS_Store'
    '**/.DS_Store'
    'snippets/*'
    'snippets/**/*'
    '*.bak'
    '.venv/*'
    '.venv/**/*'
    '.env'
    '.env.*'
    '**/.env'
    '**/.env.*'
)

ZIP_EXCLUDE_ARGS=()
for pattern in "${EXCLUDES[@]}"; do
    ZIP_EXCLUDE_ARGS+=( -x "$pattern" )
done

# .claude/ is repo-local tooling and never ships, except .claude/agents/ when a
# repo keeps plugin agents there (organon does).
build() {
    local out="$1"
    zip -r -q -X "$out" . "${ZIP_EXCLUDE_ARGS[@]}" -x '.claude/*' -x '.claude/**/*'
    if [[ -d .claude/agents ]]; then
        zip -r -q -X "$out" .claude/agents/ "${ZIP_EXCLUDE_ARGS[@]}"
    fi
}

if [[ "$DRY" -eq 1 ]]; then
    TMP_ZIP="${TMPDIR:-/tmp}/${NAME}-pkg-dry.$$.zip"
    rm -f "$TMP_ZIP"
    echo "name:        $NAME"
    echo "version:     $VERSION"
    echo "would build: $ARCHIVE"
    echo "from:        $REPO_ROOT"
    echo "contents:"
    build "$TMP_ZIP"
    unzip -l "$TMP_ZIP"
    rm -f "$TMP_ZIP"
    exit 0
fi

[[ -f "$ARCHIVE" ]] && rm -f "$ARCHIVE"
build "$ARCHIVE"

echo "built:  $ARCHIVE"
echo "size:   $(du -h "$ARCHIVE" | awk '{print $1}')"
echo "files:  $(unzip -l "$ARCHIVE" | tail -1 | awk '{print $2}')"
echo
echo "verify (must be empty):"
unzip -l "$ARCHIVE" | grep -E '(eval-workspace|__pycache__|\.DS_Store|\.git/)' || echo "  (clean)"
