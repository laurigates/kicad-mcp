#!/usr/bin/env bash
# Cut a branch from upstream/main and cherry-pick a commit onto it.
#
# Usage: prepare-branch.sh <topic-slug> <sha>
#
# Creates branch `pr-upstream/<topic-slug>` from `upstream/main`,
# attempts to cherry-pick <sha>, and reports any conflicts that need
# manual resolution.
#
# Exit codes:
#   0  branch created and cherry-pick succeeded cleanly
#   1  cherry-pick produced conflicts (branch exists, ready for manual resolution)
#   2  invalid arguments, ineligible commit, or git precondition failure

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <topic-slug> <sha>" >&2
    exit 2
fi

topic="$1"
sha="$2"
branch="pr-upstream/$topic"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Preconditions ---------------------------------------------------------

if [[ -n "$(git status --porcelain)" ]]; then
    echo "error: working tree has uncommitted changes; commit or stash first" >&2
    exit 2
fi

if git rev-parse --verify --quiet "refs/heads/$branch" >/dev/null; then
    echo "error: branch '$branch' already exists" >&2
    echo "delete it with: git branch -D $branch" >&2
    exit 2
fi

# --- Eligibility -----------------------------------------------------------

echo "==> Checking eligibility..."
if ! "$script_dir/check-eligibility.sh" "$sha"; then
    echo
    echo "Aborting — commit is not standalone-PR-able to upstream." >&2
    exit 2
fi

# --- Branch + cherry-pick --------------------------------------------------

echo
echo "==> Fetching upstream..."
git fetch upstream

echo
echo "==> Creating branch '$branch' from upstream/main..."
git checkout -b "$branch" upstream/main

echo
echo "==> Cherry-picking $sha..."
if git cherry-pick "$sha"; then
    echo
    echo "SUCCESS — cherry-pick clean."
    echo
    echo "Next steps:"
    echo "  1. Review:  git diff upstream/main..HEAD"
    echo "  2. Scrub commit message (strip local issue refs, Claude trailers, etc.):"
    echo "     PRE_COMMIT_ALLOW_NO_CONFIG=1 git -c core.commentChar='|' commit --amend"
    echo "  3. Push:    git push origin $branch"
    echo "  4. Open PR: gh pr create --repo lamaalrajih/kicad-mcp --base main \\"
    echo "                --head laurigates:$branch ..."
    exit 0
fi

echo
echo "CONFLICTS — resolve manually, then run 'git cherry-pick --continue'."
echo
echo "Conflicted files:"
git diff --name-only --diff-filter=U | sed 's/^/  - /'
echo
echo "Reminder: preserve upstream's surrounding shape, not ours."
exit 1
