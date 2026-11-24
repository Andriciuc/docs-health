---
title: "Security model and reporting"
description: "What the docs-health workflows can read and write, how inputs are validated, what to pin, and how to report a problem."
---

## What the workflows can do

| Job | Token permissions | Reads | Writes |
|---|---|---|---|
| `coverage` / `compare` | `contents: read` | This repo's scripts, plus the repos and refs you name | Run summary, a workflow artifact |
| `issue` (only when `open_issue: true`) | Whatever the caller grants; needs `issues: write` | The artifact from the job above | One issue in the calling repo |

- No secrets are needed or read. The default `GITHUB_TOKEN` is the only credential, and the analysis job's copy can only read.
- Checkouts don't keep credentials (`persist-credentials: false`), so the scripts can't reuse the token.
- Workflow inputs reach shell steps only through environment variables, never by direct `${{ }}` substitution. Repo names, refs and assignees are validated (no leading `-`, no `..`, a restricted character set). Extra inventory arguments are split with `shlex` and passed as an argument list, without a shell.
- Third-party actions are pinned to full commit SHAs, and Python dependencies to exact versions.
- The scripts read Markdown, YAML and JSON from the repos you name. YAML is loaded with a safe loader. The HTML report escapes all text, and it only renders links for `http(s)`, `mailto`, anchors and relative paths; anything else stays plain text.
- `compare.py` refuses git refs that could be read as options, and repo names outside `owner/repo`.
- Files are only read if they resolve inside the folder being scanned. A symlink pointing outside it (for example to `~/.ssh` or `/proc/self/environ`) is skipped. So are `docs_dir`, `INHERIT`, snippet and variable paths in `mkdocs.yml` that point outside the repo, and expected page names containing `..`.
- Files over 10 MB are skipped (`DOCS_HEALTH_MAX_FILE_BYTES` changes the limit), and `INHERIT` is followed at most 10 levels.
- CSV cells starting with `=`, `+`, `-` or `@` get a leading `'`, so a spreadsheet shows them as text and doesn't run them as formulas. Numbers and plain command-line flags such as `--verbose` are left alone. The HTML report shows the original text.
- git never prompts for credentials, every git call has a timeout, and the workflow jobs have `timeout-minutes`.

## Your side

- Pin `uses: …@<tag-or-sha>` and `skill_ref` to a reviewed version.
- Grant `issues: write` only if you turn `open_issue` on.
- Reports quote titles and paths from the docs you scan. Treat issue bodies from untrusted repos as untrusted text.

## Reporting a problem

Use GitHub's private vulnerability reporting (Security tab → Report a vulnerability) if it's enabled on this repo, or contact the maintainer (@Andriciuc) privately. Please don't open a public issue for security problems.
