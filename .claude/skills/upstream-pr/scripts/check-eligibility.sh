#!/usr/bin/env bash
# Check whether a commit can be cleanly cherry-picked to upstream/main.
#
# Usage: check-eligibility.sh <sha>
#
# A commit is "eligible" if its content is novel (not already applied
# upstream under a different SHA) AND every file it touches already
# exists on upstream/main. If the commit creates a fork-only file (or
# modifies one), the change cannot land standalone — its predecessor
# feature must be PR'd upstream first.
#
# Patch-id matching catches the case where upstream has re-applied our
# change with a different SHA (e.g. via a maintainer re-merge or
# squash). `git patch-id --stable` produces a content hash robust
# against rebases, cherry-picks, and trivial whitespace differences.
#
# Exit codes:
#   0  every touched file exists upstream and content is novel
#   1  at least one fork-only file
#   2  invalid arguments / git error
#   3  content already applied upstream under a different SHA

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

# --- Patch-id pre-check ---------------------------------------------------
#
# If the commit's content already exists on upstream/main under any SHA,
# there is nothing to PR. Compute patch-id for the target and compare
# against patch-ids of all non-merge commits on upstream/main.

target_patch=$(git show "$sha" | git patch-id --stable | awk '{print $1}')

if [[ -n "$target_patch" ]]; then
    # `awk ... exit` closes the pipe early on a match, which would
    # SIGPIPE-kill the upstream patch-id producer and surface as 141
    # under `set -o pipefail`. Disable pipefail just for this block.
    set +o pipefail
    match=$(
        git log --no-merges --format=%H upstream/main \
        | while read -r u; do
            printf '%s %s\n' "$(git show "$u" | git patch-id --stable | awk '{print $1}')" "$u"
          done \
        | awk -v t="$target_patch" '$1 == t { print $2; exit }'
    )
    set -o pipefail

    if [[ -n "$match" ]]; then
        match_subject=$(git log -1 --format='%s' "$match")
        echo "ALREADY APPLIED — content matches upstream commit $(git rev-parse --short "$match")"
        echo "  (\"$match_subject\")"
        echo
        echo "Nothing to PR; this change is already on upstream/main with a different SHA."
        exit 3
    fi
fi

# --- File-existence check -------------------------------------------------

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
