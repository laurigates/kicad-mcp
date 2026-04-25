---
name: upstream-pr
description: Cherry-pick a commit from this fork onto a fresh branch cut from upstream/main (lamaalrajih/kicad-mcp), ready to PR back upstream. Use when the user wants to contribute a fix back to upstream, submit an upstream PR, backport to lamaalrajih, or asks "can we send X upstream?".
---

# Upstream Contribution Workflow

This fork (`laurigates/kicad-mcp`) has substantially diverged from
`lamaalrajih/kicad-mcp`. Direct rebase is not viable. For
upstream-bound PRs, branch off `upstream/main` and cherry-pick a single
commit onto it.

## Eligibility check (always first)

Many of our changes touch fork-only files (`text_to_schematic.py`,
`sexpr_handler.py`, `visualization_tools.py`, `circuit_tools.py`,
…) and cannot land standalone — they require their predecessor
features to be PR'd upstream first.

Run:

```bash
./.claude/skills/upstream-pr/scripts/check-eligibility.sh <sha>
```

Exit code 0 = every file the commit touches exists upstream → safe to
proceed. Exit code 1 = at least one fork-only file → stop and tell the
user the change isn't standalone-PR-able.

## Prepare the branch

```bash
./.claude/skills/upstream-pr/scripts/prepare-branch.sh <topic-slug> <sha>
```

This:
1. Verifies a clean working tree
2. Re-runs the eligibility check
3. Fetches upstream
4. Creates `pr-upstream/<topic-slug>` from `upstream/main`
5. Cherry-picks `<sha>`
6. Reports any conflict files

Resolve conflicts manually. Preserve **upstream's surrounding shape**,
not ours — the goal is the smallest readable diff against upstream.

## Commit-message scrubbing

Before pushing, amend the commit message to remove fork-local context:

- **Strip local issue references** — `Closes #74`, `Addresses #19`, etc.
  Those numbers point to our fork's tracker, not upstream's.
- **Strip Claude trailers** — `Co-authored-by: Claude ...`,
  `🤖 Generated with [Claude Code]...`. Upstream doesn't follow that
  convention.
- **Soften fork-specific tooling** — if the body cites a tool upstream
  doesn't run (`bandit B607`, `ty`, `vulture`), describe the underlying
  problem instead.
- **Keep the conventional-commit prefix** — `fix(security):`,
  `feat(parser):`, etc.

Use:

```bash
PRE_COMMIT_ALLOW_NO_CONFIG=1 git -c core.commentChar='|' commit --amend -m "..."
```

The `PRE_COMMIT_ALLOW_NO_CONFIG=1` is needed because upstream has no
`.pre-commit-config.yaml` and our locally-installed pre-commit hook
otherwise refuses the commit.

## Diff hygiene

- **Don't bundle formatter cleanups** with the fix. Keep upstream's
  existing import order even if our linter would reformat.
- **One commit per PR.** If the cherry-pick produced multiple commits
  (rare), squash before pushing.
- **Verify with `git diff upstream/main..HEAD`** before pushing — every
  hunk should be defensible to a maintainer who has never seen our
  fork.

## Push and open the PR

```bash
git push origin pr-upstream/<topic-slug>

gh pr create --repo lamaalrajih/kicad-mcp --base main \
  --head laurigates:pr-upstream/<topic-slug> \
  --title "<conventional-commit subject>" \
  --body "<see body template below>"
```

### PR body template

Mirror upstream's PR template structure:

```markdown
## Description

<one or two paragraphs explaining the problem and the fix from
the maintainer's perspective — not from our fork's perspective>

## Related Issue(s)

None.  <or upstream issue numbers only>

## Type of Change

- [x] Bug fix (non-breaking change that fixes an issue)

## Testing Performed

- [x] Manually tested on macOS
- [x] `uv run pytest tests/unit -x -q` — N passed

## Notes

Originally authored on a downstream fork; the branch was cut from
`lamaalrajih/kicad-mcp:main` and a single commit cherry-picked onto
it so it applies cleanly.
```

## Reference

The first PR opened with this workflow:
https://github.com/lamaalrajih/kicad-mcp/pull/53
