# Docs vs code coverage

## Contents
- Model
- Running it
- Verifying results
- Reporting
- Writing a profile
- Limits

## Model

Code is the list of things that should be documented. A profile (`profiles/*.yml`, or a file the user provides) tells `scripts/profile_coverage.py` where those items are and what each needs in the docs. It writes them as rows of a common items CSV:

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

`scripts/coverage.py` matches items against a docs tree. Nothing in the engine is project-specific: project knowledge lives in the profile, and the rare check that doesn't fit the profile format lives in `scripts/checks/` (only `valkey_nav` today), enabled by the profile's `checks` list.

Statuses: `documented`, `missing_heading`, `undocumented`, `no_page_mentioned` (no page of its own but covered in another page), `mentioned`, `not_mentioned`, `documented_elsewhere` (found in a code-side reference file the profile marks with `also_in.counts_as_documented`, e.g. `valkey.conf`), `skipped`. Pages under `--page-glob` with no matching item go to `orphans.csv` (`no_source`, or `source_not_scanned` when they match `--ignore-glob`).

## Running it

```bash
S=path/to/docs-health/scripts
python $S/profile_coverage.py valkey --code valkey --docs valkey-doc --out cov        # built-in profile
python $S/profile_coverage.py ./their-profile.yml --code CODE --docs DOCS --out cov    # user's profile
```

Outputs: `items.csv`, `coverage.csv`, `orphans.csv`, `coverage_summary.md`, plus the output of any `checks` (Valkey: `nav_coverage.csv`, `nav_summary.md`). After writing the report (`cov/coverage-report.md`), compile the folder into one page:

```bash
python $S/html_report.py cov --title "Docs vs code coverage"   # writes cov/report.html
```

Use only the code and docs the user named (see SKILL.md, Scope). If the user has no profile for their project, draft one with them (see "Writing a profile"), run it, and show `items.csv` before reporting any gaps.

Valkey specifics: module commands (`bf.`, `json.`, `ft.`, `blob.`) live in the module repos and are ignored as orphans unless a profile extracts them. Branch choice matters: `valkey` `unstable` carries commands for the next release, so compare it with a docs branch that targets the same release, or read `since` before calling a command undocumented. A command with `since` newer than the latest release is "not yet documented", not a gap.

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

For each finding, give the count, `since`, 2–3 example items and the source file. Leave `not_mentioned` config lists out of the main report unless they were asked for. Deliver the Markdown report, the CSVs and the HTML page from `html_report.py`.

## Writing a profile

The format is documented in README.md, "Write your own profile". When drafting one for a user:
1. Find how items are declared in the code: a registration call (`DefineCustomIntVariable("…"`), a table, a file per item, an OpenAPI or JSON list. Anchor the regex on that declaration, not on the bare name.
2. Pick the docs expectation: its own page (`expect.page`) for reference items with one page each, otherwise a mention (`expect.mention`).
3. Add `skip_when` for items the code marks as internal, and `also_in` when the code ships its own reference file (a sample config).
4. Run it, open `items.csv`, and check the count against something independent (a grep, the release notes). Fix the profile before reporting gaps.
5. Add the profile to the user's repo (e.g. `.github/docs-health/<project>.yml`) and pass it to the workflow as `profile: ./.github/docs-health/<project>.yml`.

## Limits

- Presence only: a page existing and mentioning the item says nothing about whether the prose is correct.
- Mentions need code formatting (backticks, fenced code, bold). An item named only in plain prose counts as not mentioned.
- Regex profiles find only what's written literally in the code. Names built by macros or at runtime are missed; check `items.csv` against an independent count.
