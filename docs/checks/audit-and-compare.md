---
title: "Audit and compare doc sets"
description: "Inventory a doc set (stale pages, orphans, broken links, duplicates), compare two branches or repos, and join analytics exports."
---

## Inventory one doc set

```bash
git -C REPO fetch --unshallow 2>/dev/null     # shallow clones give wrong ages
python scripts/inventory.py REPO --out inv/
```

MkDocs configs (`mkdocs*.yml`, including `INHERIT`) are auto-detected. Useful flags:

| Flag | Use |
|---|---|
| `--config FILE` | Pick configs explicitly (repeatable) |
| `--docs-dir DIR` | Non-MkDocs repos, e.g. `--docs-dir .` |
| `--type-rule 'GLOB=TYPE'` | Force a topic type by path, e.g. `'commands/*.md=reference'` |
| `--bulk-commit-files N` | Ignore commits touching more than N files when computing age (default 30) |
| `--ignore-commit-subject REGEX` | Also ignore sweeps by subject, e.g. `'bump version|fix links'` |
| `--min-dup-words N` | Minimum paragraph length for duplicate detection (default 25) |

Output in `inv/`:

| File | Contents |
|---|---|
| `pages.csv` | One row per page: nav placement per config, URL, words, headings, code blocks, admonitions, tables, links in/out/broken, snippets, variables, front matter keys, topic-type guess, last meaningful commit, age |
| `nav.csv` | One row per nav entry per config: title, path, depth, section, whether the file exists |
| `links.csv` | Every internal link, image and snippet with its resolution status |
| `duplicates.csv` | Paragraphs repeated verbatim across pages |
| `summary.json` / `summary.md` | Counts and issue lists |

## Compare two sources

```bash
python scripts/compare.py valkey-io/valkey-doc@main /path/to/local/valkey-doc --out cmp/ \
  -- --docs-dir . --type-rule 'commands/*.md=reference'
```

A is the reference and B is the side being checked. Each source can be `owner/repo@ref`, a GitHub URL, a local path (working tree as-is), or `/local/path@ref`. Local repos are never modified. The output includes `pages_compare.csv`, `nav_compare.csv`, `issues_compare.csv`, `variables_compare.csv`, `commits_compare.csv`, `metrics_compare.csv` and `compare.md`.

Refs that start with `-` or contain `..` are refused, and so are repo names outside `owner/repo`. To run comparisons on a schedule, use the `docs-compare` workflow.

## Join analytics

```bash
python scripts/join_analytics.py inv/pages.csv ga4-pages.csv --out inv/joined.csv
```

URLs are normalized, and versioned prefixes (`/postgresql/19/apt.html`) match by suffix. Rows that match no page go to `unmatched.csv`; treat them as redirect candidates.
