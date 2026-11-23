# docs-architecture

A Claude skill that treats a docs-as-code set as a dataset. It inventories every page, measures freshness, links, nav coverage and duplication, and turns the numbers into a ranked architecture review. A separate reviewer agent then checks that review.

It's built for MkDocs and plain-Markdown doc repos, such as Percona Distribution for PostgreSQL, pg_tde and valkey-doc. The scripts are also usable on their own, without Claude.

## What it does

| Ask | What you get |
|---|---|
| "Audit the structure of `owner/repo`" / "what pages are stale?" | Per-page inventory (CSV) and a short report with findings, evidence, fixes, effort, and pros/cons |
| "Compare `main` and `unstable`" / "my local checkout vs upstream" | Page-by-page diff: missing, changed, renamed, nav drift, and issues fixed or introduced |
| "Restructure the nav" / "merge these pages" | Proposed nav YAML, a mapping table, redirect maps, and a migration procedure |
| "Define topic types / front matter / reuse" | Content model: types, templates, front matter schema, snippet and variable strategy |
| "Which pages matter most?" with a GA4 or Search Console export | Analytics joined to the inventory, a traffic × issue priority list, and dead URLs that need redirects |
| "Check the docs against the code" (e.g. valkey-doc vs valkey) | Commands and config options with no docs, pages for removed items, missing Reply sections, deprecated names still taught, menu and group gaps |

Every audit ends with an **optimization review** from a second agent that didn't run the scan. It confirms or disputes findings, lists quick wins, and suggests better scan flags.

## Repository layout

```
SKILL.md                  Skill entry point: scope rules, workflow, report shape
references/
  ia.md                   Information architecture checklist + restructure procedure
  content-model.md        Topic types, templates, front matter, reuse, single-sourcing
  metrics.md              Metric catalog, prioritization, coverage, analytics, CI automation
  compare.md              Two-source comparison workflow
  coverage.md             Docs vs code: running, verifying and reporting coverage
  repos.md                Known layouts of some Percona and Valkey doc repos
agents/
  optimizer.md            Prompt for the independent reviewer agent
scripts/
  inventory.py            Build the per-page dataset for one doc set
  compare.py              Run inventory.py on two sources and diff them
  join_analytics.py       Join pages.csv with a GA4 / Search Console / Plausible export
  coverage.py             Match code items against a docs tree (generic)
  extract/
    valkey_commands.py    Valkey src/commands/*.json -> items CSV
    valkey_config.py      Valkey src/config.c (+ valkey.conf) -> items CSV
  checks/
    valkey_nav.py         valkey-doc nav.yml / modules-nav / groups.json vs command JSON
tests/                    Fixtures and unit tests for the coverage scripts
.github/workflows/
  docs-coverage.yml       Reusable workflow: run the coverage checks, open a report issue
examples/
  valkey-docs-coverage.yml  Caller workflow: monthly + on demand
```

## Install

The repo root is the skill folder, since `SKILL.md` sits at the top.

**Claude Code (personal skill)**

```bash
git clone https://github.com/Andriciuc/docs-architecture.git ~/.claude/skills/docs-architecture
```

To install it for a single project instead, clone it into that project's `.claude/skills/docs-architecture/`.

**Claude apps (claude.ai, desktop)**

Build a ZIP whose top-level folder is the skill, then upload it from the Skills section of Claude's settings:

```bash
git archive --format=zip --prefix=docs-architecture/ -o docs-architecture.zip HEAD
```

When you change the skill here, upload the ZIP again. The uploaded copy doesn't follow this repo.

**Requirements for the scripts**

- Python 3.7+
- PyYAML (`pip install pyyaml`)
- git (page ages and commit counts come from history)
- Optional: pandas, for slicing the CSVs

## Using it with Claude

Name the repo, and the branch or path. The skill analyzes only the sources you name and asks if none is given.

```
/docs-architecture audit valkey-io/valkey-doc main for gaps and stale pages
/docs-architecture compare percona/postgresql-docs 18 vs 19, what's missing on 18?
/docs-architecture propose a restructure of the Get started section in ~/work/pg_tde
/docs-architecture which pages should we fix first? (attach a GA4 Pages export)
```

Claude will:

1. Run the inventory (or the comparison) before giving any opinion.
2. Open the files behind each finding to verify it. The heuristics produce false positives.
3. Write a report with a summary, findings, recommendations, a proposed structure (IA asks only), migration steps (only if pages move), and data caveats.
4. Run the optimization review as a separate agent and attach its report.

Say "no review" or "just the numbers" to skip step 4.

## Using the scripts directly

### Inventory one doc set

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

### Compare two sources

```bash
python scripts/compare.py valkey-io/valkey-doc@main /path/to/local/valkey-doc --out cmp/ \
  -- --docs-dir . --type-rule 'commands/*.md=reference'
```

A is the reference and B is the side being checked. Each source can be `owner/repo@ref`, a GitHub URL, a local path (working tree as-is), or `/local/path@ref`. Local repos are never modified. The output includes `pages_compare.csv`, `nav_compare.csv`, `issues_compare.csv`, `variables_compare.csv`, `commits_compare.csv`, `metrics_compare.csv` and `compare.md`.

### Join analytics

```bash
python scripts/join_analytics.py inv/pages.csv ga4-pages.csv --out inv/joined.csv
```

URLs are normalized, and versioned prefixes (`/postgresql/19/apt.html`) match by suffix. Rows that match no page go to `unmatched.csv`. These are redirect candidates.

### Check docs against code

Code is the list of things that should be documented. Extractors turn a code source into a common items CSV, and `coverage.py` matches it against a docs tree. Valkey example, with `valkey` and `valkey-doc` checked out side by side:

```bash
python scripts/extract/valkey_commands.py ../valkey/src/commands --out cov/items_commands.csv
python scripts/extract/valkey_config.py ../valkey/src/config.c --conf ../valkey/valkey.conf --out cov/items_config.csv
python scripts/coverage.py cov/items_commands.csv cov/items_config.csv --docs ../valkey-doc --out cov \
  --page-glob 'command=commands/*.md' \
  --ignore-glob 'commands/bf.*' --ignore-glob 'commands/json.*' --ignore-glob 'commands/ft.*' --ignore-glob 'commands/blob.*' \
  --mention-glob 'topics/*.md' --mention-glob 'commands/*.md' --exclude-glob 'topics/modules-api-ref.md'
python scripts/checks/valkey_nav.py ../valkey-doc cov/items_commands.csv --out cov
```

| File | Contents |
|---|---|
| `coverage.csv` | One row per command or config option: `documented`, `missing_heading`, `undocumented`, `no_page_mentioned`, `mentioned`, `not_mentioned`, `skipped`; pages mentioning it; deprecated pages still using it |
| `orphans.csv` | Doc pages with no source item |
| `coverage_summary.md` | Counts and gap lists |
| `nav_coverage.csv` / `nav_summary.md` | Menu coverage per command, unused menu entries, topics not listed, groups missing from `groups.json` |

A sparse clone of `valkey` (`src/commands`, `src/config.c`, `valkey.conf`) is enough. Match the code branch to the release the docs target: `unstable` carries commands that aren't released yet. To add another project (PostgreSQL GUCs, extension functions), write an extractor in `scripts/extract/` and add a test. See `references/coverage.md`.

Run the tests with `python -m unittest discover -s tests`.

## Running it as a GitHub workflow

`.github/workflows/docs-coverage.yml` is a reusable workflow. It checks out the scripts, the docs and a sparse copy of the code, runs the tests and the coverage checks, uploads the CSVs as a run artifact, and opens one report issue assigned to the owner. It has no AI step and opens no PRs. A person triages each report.

To use it, copy `examples/valkey-docs-coverage.yml` to `.github/workflows/` in the repo that should receive the issues (e.g. your fork). Then set `docs_repo`, `code_repo` and `assignee`. It runs at 06:17 UTC on the 1st of each month and from the Actions tab (Run workflow), where you can choose the branches.

Notes:
- Scheduled workflows run only from the default branch. GitHub disables them in public repos after 60 days with no repo activity.
- The caller needs `issues: write`. Set `open_issue: false` to get only the run summary and artifact.
- Pin `skill_ref` to a tag or commit if you don't want script changes to reach running workflows automatically.

## Known limits

- **Topic types** are guessed from structure (numbered steps, verb headings, tables). Spot-check them, or pin them with `--type-rule`.
- **Age** is time since the last non-bulk commit. It isn't a review date, and renames aren't followed.
- **Links** built from variables (`{{ ... }}`), absolute site URLs, anchors and external links aren't checked.
- **Duplicates** are verbatim paragraphs only. Near-duplicates and overlapping tables are missed.
- **Nav** parsing in `inventory.py` is MkDocs-only. For valkey-doc's `nav.yml`, use `scripts/checks/valkey_nav.py`.
- **Coverage** checks presence, not correctness: a page that exists and mentions an item may still be wrong. Mentions count only in code formatting (backticks, fenced code, bold).

## Contributing

Issues and PRs are welcome. Keep each change type in its own commit (scripts, references, skill instructions). For script changes, include before/after numbers from a real repo.

## License

Apache License 2.0. See [LICENSE](LICENSE).
