#!/usr/bin/env bash
# Check whether a commit can be cleanly cherry-picked to upstream/main.
#
# Usage: check-eligibility.sh <sha>
#
# A commit is "eligible" if every file it touches already exists on
# upstream/main. If the commit creates a fork-only file (or modifies
# one), the change cannot land standalone — its predecessor feature
# must be PR'd upstream first.
#
# Exit codes:
#   0  every touched file exists upstream
#   1  at least one fork-only file
#   2  invalid arguments / git error

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <sha>" >&2
    exit 2
fi

sha="$1"

if ! git rev-parse --verify --quiet "${sha}^{commit}" >/dev/null; then
    echo "error: '$sha' is not a valid commit" >&2
    exit 2
fi

if ! git rev-parse --verify --quiet upstream/main >/dev/null; then
    echo "error: upstream/main not found. Run 'git fetch upstream' first." >&2
    exit 2
fi

echo "Commit: $(git log -1 --format='%h %s' "$sha")"
echo

mapfile -t touched < <(git show --name-only --format= "$sha" | sed '/^$/d')

if [[ ${#touched[@]} -eq 0 ]]; then
    echo "error: commit touches no files" >&2
    exit 2
fi

missing=()
for path in "${touched[@]}"; do
    if git cat-file -e "upstream/main:$path" 2>/dev/null; then
        printf '  ✓ %s\n' "$path"
    else
        printf '  ✗ %s (fork-only)\n' "$path"
        missing+=("$path")
    fi
done

echo
if [[ ${#missing[@]} -eq 0 ]]; then
    echo "ELIGIBLE — all ${#touched[@]} file(s) exist on upstream/main."
    exit 0
fi

echo "NOT ELIGIBLE — ${#missing[@]} of ${#touched[@]} file(s) are fork-only:"
for path in "${missing[@]}"; do
    printf '  - %s\n' "$path"
done
echo
echo "The predecessor feature must be PR'd upstream before this commit can land."
exit 1
