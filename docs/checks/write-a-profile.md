---
title: "Write your own profile"
description: "Profile format for docs-vs-code coverage: regex, JSON and YAML sources, templates, skip rules, expectations, with an example."
---

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
