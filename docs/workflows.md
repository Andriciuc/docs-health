---
title: "GitHub workflows"
description: "Run docs-vs-code coverage and doc set comparisons on GitHub Actions, monthly or on demand, with pairs you define."
---

docs-health has two reusable workflows that anyone can call from their own repo. You define the pairs: which docs, which code or second doc set, and which refs. Both workflows are deterministic. They don't call an AI model and don't open PRs. Each run produces:

- the report in the run summary;
- an artifact with `report.html` (everything in one page) and the CSVs;
- optionally, one issue per pair for a person to triage.

Refs accept a branch, a tag, a commit, or `latest-tag` (the newest `X.Y.Z` / `vX.Y.Z` tag, release candidates excluded).

## docs-coverage: docs vs code

| Input | Default | Meaning |
|---|---|---|
| `docs_repo`, `docs_ref` | required, `main` | The docs |
| `code_repo`, `code_ref` | required, `latest-tag` | The code they document |
| `profile` | required | Built-in name (`valkey`) or `./path/to/profile.yml` in the calling repo. See [Write your own profile](checks/write-a-profile.md) |
| `name` | derived | Label for titles and artifact names |
| `open_issue`, `assignee` | `false`, empty | One issue per run in the calling repo |
| `retention_days` | `30` | Artifact retention (public repos allow up to 90) |
| `skill_repo`, `skill_ref` | `Andriciuc/docs-health`, `main` | Where the scripts come from; pin `skill_ref` |

## docs-compare: doc set A vs doc set B

| Input | Default | Meaning |
|---|---|---|
| `a_repo`, `a_ref` | required, `main` | Reference side |
| `b_repo`, `b_ref` | `a_repo`, required | Side being checked: another branch, tag, fork or repo |
| `inventory_args` | empty | Extra `inventory.py` arguments for both sides, e.g. `--docs-dir . --type-rule 'commands/*.md=reference'` |
| `history` | `true` | Full git history, so ages and one-sided commits are reported (slower) |
| `name`, `open_issue`, `assignee`, `retention_days`, `skill_repo`, `skill_ref` | | As above |

## Use it from your repo

Copy `examples/docs-coverage.yml` or `examples/docs-compare.yml` into `.github/workflows/` and edit the matrix: one entry per pair. For example, docs against `unstable` and against `latest-tag`:

```yaml
jobs:
  coverage:
    strategy:
      fail-fast: false
      matrix:
        include:
          - { name: docs vs unstable,       code_ref: unstable }
          - { name: docs vs latest release, code_ref: latest-tag }
    uses: Andriciuc/docs-health/.github/workflows/docs-coverage.yml@<tag-or-sha>
    with:
      profile: valkey                 # or ./.github/docs-health/myproject.yml in your repo
      docs_repo: valkey-io/valkey-doc
      code_repo: valkey-io/valkey
      code_ref: ${{ matrix.code_ref }}
      name: ${{ matrix.name }}
      skill_ref: <same tag-or-sha>
```

Notes:

- Pin `@<tag-or-sha>` and `skill_ref` to the same value. `@main` means every change here reaches your runs without review.
- The calling workflow needs `contents: read`, plus `issues: write` only if `open_issue` is true.
- Forks have Issues off by default, so turn them on or leave `open_issue: false`.
- Organizations may only allow actions from their own repos. An admin has to allow `Andriciuc/docs-health`.
- Scheduled workflows run from the default branch only. GitHub pauses them in public repos after 60 days without repo activity.
- Private repos as sources: the default token can only read the calling repo. Other private repos aren't supported yet.

## This repo's runs

`.github/workflows/valkey-coverage.yml` checks `valkey-io/valkey-doc@main` against `valkey-io/valkey@unstable` and `@latest-tag` on the 1st of each month, and opens one issue per pair assigned to the owner. Run it on demand from Actions → **Valkey docs coverage** → **Run workflow**: leave `code_ref` empty for both presets, or enter any branch, tag or `latest-tag`. It only reads the valkey-io repos.
