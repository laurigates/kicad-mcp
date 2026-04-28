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

Exit codes:

- **0** — every file the commit touches exists upstream and content is
  novel → safe to proceed.
- **1** — at least one fork-only file → stop and tell the user the
  change isn't standalone-PR-able.
- **3** — content already applied upstream under a different SHA →
  nothing to PR. The script reports the matching upstream commit. This
  catches re-applied content (e.g. maintainer re-merges or squashes)
  via `git patch-id --stable` matching against every non-merge commit
  on `upstream/main`.

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

## When cherry-pick fails: re-derive on upstream

If the cherry-pick produces dozens of conflict blocks across multiple
files (typical when upstream and fork have drifted heavily on shared
modules), abort and re-derive instead of fighting hunks.

```bash
git cherry-pick --abort
git checkout -b pr-upstream/<topic-slug> upstream/main
# Re-apply the change against upstream's actual current files.
```

Re-derive is the right call when:

- The fork commit performs a **mechanical, re-applicable transform**
  (e.g. `print()` → logging, deprecation rename, lint-rule
  auto-fixes) — the rules transfer cleanly even if line numbers don't.
- Upstream's version of the file has **additional lines our fork
  removed** — re-derive lets you cover them with the same heuristic
  rather than rationalizing missing hunks.
- The cherry-pick conflict count exceeds roughly **20 blocks across
  >2 files**.

Heuristic: extract the original commit's `before → after` map (e.g.
`git show <sha> | grep -E '^[-+].*pattern'`) and use it as the rulebook
when re-applying against upstream. The PR body should disclose the
re-derive (see template below).

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
  existing import order even if our linter would reformat. (Upstream
  may have unusual indentation — e.g. 21-space rather than 20-space
  blocks. Preserve it; Edit-tool replacements that change leading
  whitespace by even one character will break the parse.)
- **One commit per PR.** If the cherry-pick produced multiple commits
  (rare), squash before pushing.
- **Verify with `git diff upstream/main..HEAD`** before pushing — every
  hunk should be defensible to a maintainer who has never seen our
  fork.

### Pre-flight: prove you didn't introduce regressions

For refactor / cleanup PRs, verify lint and test parity against the
**pristine upstream baseline**, not against our fork. Use a stash
roundtrip to A/B compare:

```bash
# Baseline (pristine upstream/main):
git stash push -- <changed-files>
uv run ruff check --output-format=concise <changed-files> 2>&1 | tail -1   # error count
uv run pytest tests/ -q 2>&1 | tail -1                                     # pass count
git stash pop

# After (with your changes): run the same two commands and compare.
```

Both numbers must match (or improve). The pre-flight catches: stray
formatter touches, accidental import reordering, indentation drift
from Edit-tool replacements. Quote both numbers in the PR body's
"Testing Performed" section.

Also run `python3 -c "import ast; ast.parse(open(F).read())"` on every
edited Python file — catches indentation breaks that ruff might miss
on already-warning-laden upstream code.

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

PRs opened with this workflow, by path:

| PR | Path | Notes |
|---|---|---|
| [#53](https://github.com/lamaalrajih/kicad-mcp/pull/53) | cherry-pick | First PR; clean apply |
| [#54](https://github.com/lamaalrajih/kicad-mcp/pull/54) | cherry-pick + 1 conflict | CI workflow; resolved by keeping upstream's shape |
| [#55](https://github.com/lamaalrajih/kicad-mcp/pull/55) | re-derive | 5-file refactor; fork drift made cherry-pick infeasible |
