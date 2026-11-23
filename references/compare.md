# Compare two doc sets

## Contents
- Sources
- Run
- Reading the output
- Local checkouts on the user's computer
- Report shape
- Pitfalls

## Sources

| User says | A (reference) | B (checked) |
|---|---|---|
| "unstable vs main" | `owner/repo@main` | `owner/repo@unstable` (or the reverse; say which you chose) |
| "my local vs unstable" | `owner/repo@unstable` | `/path/to/local` (working tree, uncommitted edits included) |
| "local branch X vs upstream" | `owner/repo@main` | `/path/to/local@X` |
| "18 vs 19" | `percona/postgresql-docs@18` | `percona/postgresql-docs@19` |
| "our docs vs theirs" | the competitor or upstream repo | ours. Only nav/pages/metrics are meaningful; commits won't be shared |

Branch names differ across repos. valkey-io/valkey uses `unstable`, while valkey-io/valkey-doc uses `main` plus release branches. Check with `git ls-remote --heads https://github.com/OWNER/REPO.git` before assuming one exists.

## Run

```bash
python scripts/compare.py A B --out cmp/ [--label-a main --label-b unstable] [-- INVENTORY_ARGS]
# e.g.
python scripts/compare.py valkey-io/valkey-doc@main /path/to/valkey-doc --out cmp/ -- --type-rule 'commands/*.md=reference'
```

- Remote sources are cloned into `--work` (default `.docs-compare/`). One clone is shared per repo, with a worktree for the second ref. Rerunning fetches updates.
- `path@ref` reads a ref of a local repo through a `--shared` clone in `--work`. The user's repo is never written to: no worktrees, no fetches into it.
- Full history is used by default, so ages and commits are real. `--shallow` is faster but makes `newer_side` and commit lists unreliable.

## Reading the output

| File / status | Means | Usual action |
|---|---|---|
| `pages_compare.csv` `only_a` | A has the page, B doesn't | Missing in B: port it, or confirm it was removed on purpose (check `commits_compare.csv` for a deletion) |
| `only_b` | New in B | Missing in A if A should have it (e.g. a fix made on a release branch only) |
| `renamed` (similarity ≥ threshold) | Same content, new path | Needs a redirect if B is published. Release notes are never matched as renames |
| `changed` + `newer_side=a` | A edited after B | B is probably behind. Diff the page and port it |
| `changed` + `newer_side=b` | B edited after A | Expected for the branch being worked on; check that it doesn't undo a fix from A |
| `headings_added/removed` | Structural change inside a page | Anchors may break; grep for links to removed headings |
| `nav_compare.csv` `moved` / `relabeled` / `only_*` | IA differs between sides | Decide which tree is intended and apply it to the other (ia.md → Restructure procedure) |
| `issues_compare.csv` `introduced_in_b` | Broken link, undefined variable, orphan, or missing nav file that A doesn't have | Fix before merging or releasing B |
| `fixed_in_b` | A still has it | Port the fix to A |
| `variables_compare.csv` | Version strings and dates per side | Expected for version bumps. Anything else (URLs, product names) is drift |
| `commits_compare.csv` `only_a` | Docs commits on A not reachable from B | The backport/merge list. Read the subjects and group them by page |
| `metrics_compare.csv` | Side-by-side health | Headline deltas for the report |

Similarity is line-level (0–1). Below ~0.8 means substantial rewrites, and ≥0.98 is usually typos or variables.

## Local checkouts on the user's computer

The script needs the local repo on a disk it can read, with its `.git` folder.
- **Claude Code on the user's machine:** pass the path directly (Windows/Git Bash: `/c/Users/...` or `C:/Users/...`).
- **Cloud session with a device shell** (`device_bash`) on the user's computer: run `compare.py` there, after checking Python and PyYAML are installed (`python -c "import yaml"`).
- **Cloud session without a shell:** staging individual files loses git history. Either ask the user to push the branch and compare `owner/repo@branch`, or ask them to zip the repo including `.git` and attach it. Say what is lost: uncommitted edits in the first case, nothing in the second.

## Report shape

```markdown
# <A> vs <B>: docs comparison
## Summary            ≤5 bullets with counts: missing in B, new in B, behind, issues introduced/fixed
## Missing or behind  table: page | status | evidence (commit, similarity, date) | action
## Structure          nav differences that matter (not every release-notes entry)
## Issues             introduced in B / fixed in B
## Variables          only unexpected differences
## Port list          commits_compare only_a grouped by page, with a suggested cherry-pick order
## Data & caveats     commands, which side is A, shallow history, intentional differences assumed
```

Filter out the expected noise before reporting. Version bumps, a release branch's own release notes, and pages deliberately removed in one version shouldn't be listed as problems. List them once as "expected differences" so the reader can see they were considered.

## Pitfalls

- **Stale branches dominate.** A branch cut months ago shows hundreds of "changed" pages. Lead with `commits_compare` and `newer_side` so the reader sees direction, not just volume.
- **Different `docs_dir` or configs per side** (a restructure between versions). Nav comparison only covers configs with the same file name, and the script lists configs that exist on one side only.
- **Comparing different repos** (fork vs upstream with no shared history): the commit list is empty, so rely on page status, similarity, and dates.
- **Generated pages** (e.g. Valkey command pages built from JSON). Differences may come from the generator, not the Markdown, so check the data source.
