# docs-health

A Claude skill and GitHub workflow that treats a docs-as-code set as a dataset. It inventories every page, measures freshness, links, nav coverage and duplication, checks the docs against the code they describe and audits SEO metadata, then turns the numbers into a ranked review. A separate reviewer agent then checks that review.

It's built for MkDocs and plain-Markdown doc repos, such as Percona Distribution for PostgreSQL, pg_tde and valkey-doc. The scripts are also usable on their own, without Claude.

## What it does

| Ask | What you get |
|---|---|
| "Audit the structure of `owner/repo`" / "what pages are stale?" | Per-page inventory (CSV) and a short report with findings, evidence, fixes, effort, and pros/cons |
| "Compare `main` and `unstable`" / "my local checkout vs upstream" | Page-by-page diff: missing, changed, renamed, nav drift, and issues fixed or introduced |
| "Restructure the nav" / "merge these pages" | Proposed nav YAML, a mapping table, redirect maps, and a migration procedure |
| "Define topic types / front matter / reuse" | Content model: types, templates, front matter schema, snippet and variable strategy |
| "Which pages matter most?" with a GA4 or Search Console export | Analytics joined to the inventory, a traffic × issue priority list, and dead URLs that need redirects |
| "Check the docs against the code" (any project, via a profile; Valkey built in) | Commands, settings or other items with no docs, pages for removed items, missing Reply sections, deprecated names still taught, menu and group gaps |
| "Run this every month" / "compare `unstable` and the latest tag on GitHub" | Reusable GitHub workflows for coverage and compare, with your own pairs: a run summary, a `report.html` artifact, and optionally one issue per pair. See [Running it as a GitHub workflow](#running-it-as-a-github-workflow) |
| "Check our titles and descriptions" / "SEO pass" | A separate metadata report: whether the build emits titles and descriptions, missing, duplicate and UI-label titles, H1 problems, boilerplate prefixes, and proposed rewrites for the top pages, checked against Google Search Central rules |

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
  google-metadata-rules.md   Google Search Central: titles, rewrites, snippets, robots, canonicals
  docs-frontmatter-patterns.md  Docs-specific SEO: titles, front matter template, build check, versions, JSON-LD, GEO
  seo-sources.md          Official specs, platform guides and books behind the SEO rules
  repos.md                Known layouts of some Percona and Valkey doc repos
agents/
  optimizer.md            Prompt for the independent reviewer agent
scripts/
  inventory.py            Build the per-page dataset for one doc set
  compare.py              Run inventory.py on two sources and diff them
  join_analytics.py       Join pages.csv with a GA4 / Search Console / Plausible export
  coverage.py             Match items against a docs tree (used by profile_coverage.py)
  html_report.py          Compile a scan folder's Markdown and CSVs into one HTML page
  metadata_check.py       Titles, descriptions and H1s from front matter (SEO step)
  profile_coverage.py     Docs vs code for any project, driven by a YAML profile
  checks/
    valkey_nav.py         Optional Valkey-only check: nav.yml / modules-nav / groups.json vs command groups
profiles/
  valkey.yml              Built-in profile: valkey commands and config vs valkey-doc
tests/                    Fixtures, unit tests and security regression tests
.github/workflows/
  docs-coverage.yml       Reusable: docs vs code, for any pair you define
  docs-compare.yml        Reusable: doc set A vs doc set B, for any pair you define
  valkey-coverage.yml     This repo's runs: valkey-doc vs valkey unstable and vs the latest tag
  ci.yml                  Tests plus smoke runs of both reusable workflows on every PR
examples/
  docs-coverage.yml       Caller template: matrix of docs-vs-code pairs
  docs-compare.yml        Caller template: scheduled pairs + a one-off pair from the Run workflow form
SECURITY.md               What the workflows can access, and how to report a problem
```

## Install

The repo root is the skill folder, since `SKILL.md` sits at the top.

**Claude Code (personal skill)**

```bash
git clone https://github.com/Andriciuc/docs-health.git ~/.claude/skills/docs-health
```

To install it for a single project instead, clone it into that project's `.claude/skills/docs-health/`.

**Claude apps (claude.ai, desktop)**

Build a `.skill` file whose top-level folder is the skill, then upload it from the Skills section of Claude's settings:

```bash
git archive --format=zip --prefix=docs-health/ -o docs-health.skill HEAD SKILL.md README.md LICENSE SECURITY.md agents references scripts profiles
```

The `.skill` file is a ZIP with the skill folder at the top; the tests, fixtures and workflows stay in the repo. When you change the skill here, upload the file again: the uploaded copy doesn't follow this repo.

Renamed from `docs-architecture`: if you installed the old name, delete it from your skills so Claude doesn't see two copies. GitHub redirects the old repo URL.

**Requirements for the scripts**

- Python 3.7+
- PyYAML (`pip install pyyaml`)
- git (page ages and commit counts come from history)
- Optional: pandas, for slicing the CSVs

## Using it with Claude

Name the repo, and the branch or path. The skill analyzes only the sources you name and asks if none is given.

```
/docs-health audit valkey-io/valkey-doc main for gaps and stale pages
/docs-health compare percona/postgresql-docs 18 vs 19, what's missing on 18?
/docs-health propose a restructure of the Get started section in ~/work/pg_tde
/docs-health which pages should we fix first? (attach a GA4 Pages export)
```

Claude will:

1. Run the inventory (or the comparison) before giving any opinion.
2. Open the files behind each finding to verify it. The heuristics produce false positives.
3. Write a report with a summary, findings, recommendations, a proposed structure (IA asks only), migration steps (only if pages move), and data caveats.
4. Run the optimization review as a separate agent and attach its report.
5. Compile the report, the review, the summaries and the CSVs into one HTML page (`report.html`).
6. Optionally, run a separate metadata and SEO pass with its own report. It runs when you ask for it, and Claude offers it after an audit.

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

Refs that start with `-` or contain `..` are refused, and so are repo names outside `owner/repo`. To run comparisons on a schedule, use the `docs-compare` workflow.

### Metadata and SEO check

```bash
python scripts/metadata_check.py ../valkey-doc --glob 'topics/*.md' --out meta \
  --title-template 'Valkey Documentation · {title}'
```

It reads front matter (`title`, `description`; change the keys with `--title-key`/`--desc-key`) and H1s. Then it writes `metadata.csv` and `metadata_summary.md`, with issues graded `error` (missing or duplicate title), `warn` (missing or duplicate description, one-word title, body H1 next to a front-matter title, several H1s) and `info` (lengths, title/H1 mismatch, shared title prefixes). `--title-template` applies the site's title format, so length checks match the real `<title>`.

It checks sources only. Whether the site emits these fields is a separate check: `references/docs-frontmatter-patterns.md` → "Check the build".

### HTML report

Every scan folder can be compiled into one self-contained HTML page: all Markdown reports rendered (main report first), and every CSV/TSV as a table you can sort by clicking a header and filter by typing.

```bash
python scripts/html_report.py inv/                                   # writes inv/report.html
python scripts/html_report.py cov/ inv/ --out review.html --title "Valkey docs review"
```

The page has no external assets and uses ES5 script only. It opens offline in any browser, including old ones, so you can attach it, email it or publish it as is. Tables over `--max-rows` (default 5000) are cut, with a note pointing to the full CSV. When Claude runs the skill, it builds this page at the end of every scan.

### Join analytics

```bash
python scripts/join_analytics.py inv/pages.csv ga4-pages.csv --out inv/joined.csv
```

URLs are normalized, and versioned prefixes (`/postgresql/19/apt.html`) match by suffix. Rows that match no page go to `unmatched.csv`. These are redirect candidates.

### Check docs against code

Code is the list of things that should be documented. A **profile** (a small YAML file) says where those things are in the code and what each one needs in the docs. `profile_coverage.py` extracts them and checks the docs. Valkey example, with `valkey` and `valkey-doc` checked out side by side:

```bash
python scripts/profile_coverage.py valkey --code ../valkey --docs ../valkey-doc --out cov
```

`valkey` is the built-in profile (`profiles/valkey.yml`). Pass a path instead to use your own: `python scripts/profile_coverage.py ./my-profile.yml --code … --docs …`.

| File | Contents |
|---|---|
| `items.csv` | Everything the profile extracted from the code |
| `coverage.csv` | One row per item: `documented`, `missing_heading`, `undocumented`, `no_page_mentioned`, `mentioned`, `not_mentioned`, `documented_elsewhere`, `skipped`; pages mentioning it; deprecated pages still using it |
| `orphans.csv` | Doc pages with no matching item (removed or renamed in the code) |
| `coverage_summary.md` | Counts and gap lists |
| `nav_coverage.csv` / `nav_summary.md` | Valkey profile only: menu coverage, unused menu entries, groups missing from `groups.json` |

Match the code branch to the release the docs target: development branches carry items that aren't released yet.

### Write your own profile

Any project works if its documentable items can be found by a regex, or read from JSON or YAML files: commands, config options, CLI flags, API endpoints, SQL functions, error codes. Start from `profiles/valkey.yml`. A profile for a C extension with settings, SQL functions and a JSON API list might look like this:

```yaml
name: myproject
code:
  sparse: [src, sql, api.json]          # what the workflow checks out; omit for a full checkout
docs:
  page_globs: { endpoint: reference/*.md }      # pages that should each match an item (others = orphans)
  mention_globs: ["docs/**/*.md"]               # where mentions are searched
  exclude_globs: ["docs/generated/**"]          # never searched
items:
  - kind: setting                       # GUC-style settings declared in C
    source: regex
    files: ["src/**/*.c"]
    pattern: 'DefineCustom\w+Variable\(\s*"(?P<name>myproject\.[a-z_]+)"'
    expect: { mention: true }

  - kind: function                      # SQL functions from install scripts
    source: regex
    files: ["sql/*.sql"]
    pattern: 'CREATE (?:OR REPLACE )?FUNCTION\s+(?P<name>myproject_\w+)\s*\('
    flags: [IGNORECASE, MULTILINE]
    expect: { mention: true }

  - kind: endpoint                      # [{"endpoint": "list-users", "method": "GET", "internal": false}, ...]
    source: json
    files: [api.json]
    id: "{endpoint}"
    name: "{method} {endpoint}"
    skip_when:
      - { field: internal, equals: "true", reason: internal }
    expect:
      page: "reference/{endpoint}.md"
      heading: { text: Response }
```

Item keys:

| Key | Meaning |
|---|---|
| `kind` | Item type, used in reports and `page_globs` (one word) |
| `source` | `regex`, `json` or `yaml` |
| `files` | Globs relative to the code folder (`**` allowed, no `..`) |
| `pattern`, `flags` | `regex` only. Named groups become fields; `name` (or the first group) is the item. Flags: `MULTILINE` (default), `DOTALL`, `IGNORECASE` |
| `each` | `json`/`yaml` only: dotted path to a list or map of items inside each file. A file whose top level is a list gives one item per entry |
| `unwrap: single-key` | `json`/`yaml`: the file is `{"NAME": {...}}`, so `NAME` becomes `{key}` |
| `id`, `name`, `aliases` | Templates. `{field}` is replaced by a field's value; `{stem}`, `{path}` and `{file}` describe the source file. `id` must be unique per kind; `aliases` is `;`-separated |
| `fields` | Extra columns, as templates. `deprecated_since` and `replaced_by` (with the replacement in backticks) enable the "deprecated but still taught" check |
| `skip_when` | List of conditions that mark an item as not meant to be documented: `{field, contains}`, `{field, equals}` or `{field, matches}`, plus an optional `reason` |
| `expect` | `{mention: true}`: must appear in code formatting (backticks, code block or bold) in `mention_globs`. Or `{page: "…{id}…"}`: needs its own page, optionally with `heading: {text, when_field}` |
| `also_in` | A code-side reference file to look in too (`files`, `pattern` with one group, `column`). With `counts_as_documented: true`, an item found there but not in the docs is `documented_elsewhere` instead of a gap |

Profile-level keys: `name`, `code.sparse`, `docs.page_globs` / `ignore_globs` / `mention_globs` / `exclude_globs`, and `checks` (extra built-in checks; currently only `valkey_nav`).

Tips:
- Run it locally against a checkout first, and open `items.csv`. If items are missing or wrong, fix the pattern before trusting any gaps.
- Keep regexes anchored to how items are declared, not just to their name, or comments and tests will match too.
- A profile can't run code. Templates only substitute fields, and `checks` come from a fixed list. Profiles from untrusted sources are still worth reading before you run them.

Run the tests with `python -m unittest discover -s tests`.

## Running it as a GitHub workflow

Two reusable workflows, which anyone can call from their own repo. You define the pairs: which docs, which code or which second doc set, and which refs. Both are deterministic, with no AI step and no PRs. Each run produces:
- the report in the run summary;
- an artifact with `report.html` (everything in one page) and the CSVs;
- optionally, one issue per pair for a person to triage.

Refs accept a branch, a tag, a commit, or `latest-tag` (the newest `X.Y.Z` / `vX.Y.Z` tag, release candidates excluded).

### docs-coverage: docs vs code

| Input | Default | Meaning |
|---|---|---|
| `docs_repo`, `docs_ref` | required, `main` | The docs |
| `code_repo`, `code_ref` | required, `latest-tag` | The code they document |
| `profile` | required | Built-in name (`valkey`) or `./path/to/profile.yml` in the calling repo. See [Write your own profile](#write-your-own-profile) |
| `name` | derived | Label for titles and artifact names |
| `open_issue`, `assignee` | `false`, empty | One issue per run in the calling repo |
| `retention_days` | `30` | Artifact retention (public repos allow up to 90) |
| `skill_repo`, `skill_ref` | `Andriciuc/docs-health`, `main` | Where the scripts come from; pin `skill_ref` |

### docs-compare: doc set A vs doc set B

| Input | Default | Meaning |
|---|---|---|
| `a_repo`, `a_ref` | required, `main` | Reference side |
| `b_repo`, `b_ref` | `a_repo`, required | Side being checked: another branch, tag, fork or repo |
| `inventory_args` | empty | Extra `inventory.py` arguments for both sides, e.g. `--docs-dir . --type-rule 'commands/*.md=reference'` |
| `history` | `true` | Full git history, so ages and one-sided commits are reported (slower) |
| `name`, `open_issue`, `assignee`, `retention_days`, `skill_repo`, `skill_ref` | | As above |

### Use it from your repo

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

### This repo's runs

`.github/workflows/valkey-coverage.yml` checks `valkey-io/valkey-doc@main` against `valkey-io/valkey@unstable` and `@latest-tag` on the 1st of each month, and opens one issue per pair assigned to the owner. Run it on demand from Actions → **Valkey docs coverage** → **Run workflow**: leave `code_ref` empty for both presets, or enter any branch, tag or `latest-tag`. It only reads the valkey-io repos.

## Known limits

- **Topic types** are guessed from structure (numbered steps, verb headings, tables). Spot-check them, or pin them with `--type-rule`.
- **Age** is time since the last non-bulk commit. It isn't a review date, and renames aren't followed.
- **Links** built from variables (`{{ ... }}`), absolute site URLs, anchors and external links aren't checked.
- **Duplicates** are verbatim paragraphs only. Near-duplicates and overlapping tables are missed.
- **Nav** parsing in `inventory.py` is MkDocs-only. For valkey-doc's `nav.yml`, use `scripts/checks/valkey_nav.py`.
- **Coverage** checks presence, not correctness: a page that exists and mentions an item may still be wrong. Mentions count only in code formatting (backticks, fenced code, bold).

## Security

The workflows read public repos, run the scripts in this repo, and only write when `open_issue` is on, and then only one issue in the calling repo. Details and reporting: [SECURITY.md](SECURITY.md).

## Contributing

Issues and PRs are welcome. Every PR runs CI (`ci.yml`): the unit and security tests, plus a smoke run of both reusable workflows against valkey-doc and valkey. Keep each change type in its own commit (scripts, references, skill instructions). For script changes, include before/after numbers from a real repo.

## License

Apache License 2.0. See [LICENSE](LICENSE).
