# Docs vs code coverage

## Contents
- Model
- Running it (Valkey)
- Verifying results
- Reporting
- Adding a source
- Limits

## Model

Code is the list of things that should be documented. Each extractor in `scripts/extract/` turns one code source into rows of a common items CSV:

| column | meaning |
|---|---|
| `kind` | `command`, `config`, `function`… |
| `id` | stable key; for page-based items, the page file stem |
| `name` | display name, used for mention matching (`ACL SETROLE`) |
| `aliases` | `;`-separated alternative names |
| `expected_page` | page that must exist (`commands/get.md`), or empty for mention-only items |
| `require_heading` | heading the page must have (`Reply` when the JSON has a reply schema) |
| `skip_reason` | set when the code says it isn't meant to be documented (`SYSCMD`, `HIDDEN_CONFIG`) |
| `deprecated_since`, `replaced_by` | used to flag deprecated items the docs still teach |

`scripts/coverage.py` matches items against a docs tree. It knows nothing about Valkey: anything project-specific belongs in an extractor or in `scripts/checks/`.

Statuses: `documented`, `missing_heading`, `undocumented`, `no_page_mentioned` (no page of its own but covered in another page), `mentioned`, `not_mentioned`, `skipped`. Pages under `--page-glob` with no matching item go to `orphans.csv` (`no_source`, or `source_not_scanned` when they match `--ignore-glob`).

## Running it (Valkey)

Inputs: a `valkey` checkout (`src/commands/`, `src/config.c`, `valkey.conf`) and a `valkey-doc` checkout. A sparse clone of `valkey` with `src/commands` and `src/config.c` is enough. Module commands come from the module repos (`valkey-bloom`, `valkey-json`, `valkey-search`, `valkey-large-object`). If you don't extract them, ignore their pages.

```bash
S=path/to/docs-architecture/scripts
python $S/extract/valkey_commands.py valkey/src/commands --out cov/items_commands.csv
python $S/extract/valkey_config.py valkey/src/config.c --conf valkey/valkey.conf --out cov/items_config.csv
python $S/coverage.py cov/items_commands.csv cov/items_config.csv --docs valkey-doc --out cov \
  --page-glob 'command=commands/*.md' \
  --ignore-glob 'commands/bf.*' --ignore-glob 'commands/json.*' --ignore-glob 'commands/ft.*' --ignore-glob 'commands/blob.*' \
  --mention-glob 'topics/*.md' --mention-glob 'commands/*.md' --exclude-glob 'topics/modules-api-ref.md'
python $S/checks/valkey_nav.py valkey-doc cov/items_commands.csv --out cov
```

Outputs: `coverage.csv`, `orphans.csv`, `coverage_summary.md`, `nav_coverage.csv`, `nav_summary.md`.

To add module commands, pass more directories to `valkey_commands.py` (e.g. `valkey-json/src/commands`) and drop the matching `--ignore-glob`.

Branch choice matters. `valkey` `unstable` carries commands for the next release. Compare it with a docs branch that targets the same release, or read `since` before calling a command undocumented. A command with `since` newer than the latest release is "not yet documented", not a gap.

## Verifying results

Open the source behind each class of finding before reporting it:
- `undocumented`: open the JSON (`since`, `group`, `doc_flags`) and grep the docs for the name in any form. Several command families (e.g. `SENTINEL *`) are documented inside a topic by design, and they show up as `no_page_mentioned`. If one shows as `undocumented`, the topic doesn't mention it even in prose.
- `missing_heading`: check whether the page describes the reply in prose (still a template gap, lower severity) and whether the page is a container (`hotkeys.md`), alias or internal command.
- `deprecated_in_use`: read the surrounding text. Docs explaining a rename on purpose are fine. Docs teaching the old name as the main one are not.
- Config `not_mentioned`: informational only. For Valkey, `valkey.conf` is the config reference, so check `in_conf` first. Only `in_conf=no` is a real gap.
- Orphans `no_source`: usually module commands whose JSON wasn't extracted (find the prefix, add `--ignore-glob`) or a command that was removed or renamed.

## Reporting

Lead with code-side gaps, because they're the least arguable:
1. Released items with no docs (group by feature: a new data type is one finding, not 12).
2. Deprecated names the docs still teach as primary.
3. Missing required sections on recent pages.
4. Website-facing metadata gaps (`groups.json`, menu groups).

For each finding, give the count, `since`, 2–3 example items and the source file. Leave `not_mentioned` config lists out of the main report unless they were asked for.

## Adding a source

Write `scripts/extract/<project>_<thing>.py` that outputs the common columns (import `FIELDS` from `valkey_commands.py`), plus any extra columns of its own. Examples:
- PostgreSQL GUCs: `src/backend/utils/misc/postgresql.conf.sample` or `guc_tables.c` → `kind=config`, mention-only.
- Extension SQL functions: `*.sql` install scripts (`CREATE FUNCTION name(`) → `kind=function`, mention-only.
- pg_tde GUCs: `DefineCustom*Variable("pg_tde.…"` in the C source.

Add a fixture and a test in `tests/` for every extractor.

## Limits

- Presence only: a page existing and mentioning the item says nothing about whether the prose is correct.
- Mentions need code formatting (backticks, fenced code, bold). An item named only in plain prose counts as not mentioned.
- `config.c` parsing expects one `create*Config("name", alias, FLAGS, …)` call per option. Macros that build names dynamically are missed.
