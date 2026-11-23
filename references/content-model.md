# Content model

## Contents
- Topic types
- Split rules
- Front matter schema
- Templates
- Reuse: snippets vs variables vs duplication
- Single-sourcing (HTML + PDF, base + override configs)
- Pages generated from data
- Enforcing the model

## Topic types

The vocabularies map to each other. Use the one the team already speaks, and put the mapping in the style guide once.

| Diátaxis | DITA | Red Hat modular | Must have | Must not have |
|---|---|---|---|---|
| How-to | task | procedure | One goal in the title, prerequisites, numbered steps, a verification step, next steps | Background longer than ~2 sentences, or alternatives inline (link to them instead) |
| Tutorial | task (learning) | procedure inside an assembly | A guaranteed-success path, a stated end state, copy-pasteable commands | Choices, or production caveats in the main flow |
| Reference | reference | reference | Consistent per-item structure (name, type, default, description), scannable tables or definition lists, stable ordering | Procedures, or opinions |
| Explanation | concept | concept | The "why" and "how it works", diagrams, trade-offs, links to tasks | Steps |
| — | map | assembly | Ordered links + short glue text | Original content beyond intros |

Inventory signals (`type_guess`): ordered-list items, imperative headings, and code blocks point to a task. Tables point to reference. Few words with many links point to a landing page. `mixed` = several strong signals on a long page, which makes it the first split candidate.

## Split rules

Split a page when any of these holds:
- It contains ≥2 types, and either it is > ~1,500 words or one part is linked to on its own (anchor links in `links.csv` show this).
- It has more than one H1, or H2s that each have their own prerequisites.
- It mixes platforms or versions in parallel branches. Use content tabs only when the branches are short and the same length. Otherwise use separate pages under a section index.

Don't split when the pieces would be < ~200 words each and are always read together.

## Front matter schema

Add a field only if something consumes it (search, the tags index, a validation script, a dashboard, a PR checklist). Unconsumed fields rot.

| Field | Type | Consumer | Notes |
|---|---|---|---|
| `title` | str | Material page title, search | Only needed when it should differ from the H1 |
| `description` | str ≤160 | `<meta>`, social cards, search snippets | Strong SEO and search win, cheap to add |
| `content_type` | enum: how-to, tutorial, reference, explanation, landing, release-notes | Validation, inventory, dashboards | Turns the heuristic `type_guess` into data you can trust |
| `tags` | list | Material `tags` plugin, tag index pages | A controlled vocabulary lives in one file, and the validator rejects anything not in it |
| `applies_to` | list of versions/components | Version banners, filtering | Only if pages differ across versions within one branch |
| `owner` | str (team or person) | Review routing, staleness reports | Optional. Can map to CODEOWNERS instead |
| `last_reviewed` | date | Freshness metric (true review date, not commit date) | Only worth it if reviews actually happen. Otherwise it lies |
| `status` | enum: draft, beta, ga, deprecated | Banners, excludes | Pair with the material `status` page metadata if used |

Pros of front matter as the model: it is versioned with the content, survives moves, and is cheap to validate. Cons: authors forget it, so it needs CI enforcement, and bulk-adding it creates a huge diff. Roll it out per section. Alternative: keep metadata in a sidecar YAML keyed by path. That is easier to bulk-edit, but it drifts on renames.

## Templates

One skeleton per type in `templates/` (outside `docs_dir` or excluded from the build). Keep the skeletons minimal. Here is a how-to:

```markdown
---
content_type: how-to
description: <one sentence: what you'll achieve>
---
# <Verb> <object>

<1–2 sentences: when you'd do this.>

## Prerequisites

* ...

## Procedure

1. ...

    ```{.bash data-prompt="$"}
    $ ...
    ```

## Verify

...

## Next steps

* [...](...)
```

Match the repo's existing conventions (code-fence attributes, admonition styles, variable names). Read 2–3 existing pages of the same type before writing a template.

## Reuse: snippets vs variables vs duplication

| Mechanism | Use for | Pros | Cons |
|---|---|---|---|
| Variables (`mkdocs-macros` + `variables.yml`) | Version numbers, product names, dates, URLs that change per release | One edit per release, and it works inside code blocks | Undefined variables render as blank or raw text. Logic in Jinja templates is hard to review |
| Snippets (`pymdownx.snippets`, `--8<--`) | Identical blocks that must change together: repo setup, supported-version tables, common prerequisites | Single source, and the files stay plain Markdown | Heading levels are fixed by the snippet. The context is invisible while you edit. Broken paths fail quietly unless `check_paths: true` |
| Duplication | Text that looks the same but should be allowed to diverge per context | Each page reads standalone and can be edited independently | Fixes get applied in one place and missed in the others |

Use `duplicates.csv`. A group of ≥3 pages with the same paragraph that must stay in sync is a snippet candidate. A group of 2 is usually fine to leave. Snippet hygiene: keep snippets outside `docs_dir` (or excluded) so they aren't built as pages, don't put headings in snippets that get included at different levels, and set `check_paths: true` so a broken include fails the build.

## Single-sourcing (HTML + PDF, base + override configs)

When `mkdocs.yml` and `mkdocs-pdf.yml` both `INHERIT` from a base, any config that redefines `nav` replaces the base nav entirely. Drift is guaranteed over time, and the inventory's `nav_drift` measures it.

| Option | Pros | Cons |
|---|---|---|
| Nav only in base, children don't redefine it | One source, no drift | The PDF can't easily omit pages (handle it with the PDF plugin's exclude options, or accept the full set) |
| Separate navs + CI drift check (inventory nav_drift must be empty or match an allow-list) | Intentional differences are allowed | Two places to edit, and the CI check needs maintaining |
| Generate PDF nav from HTML nav with a script | No manual drift | Custom tooling to own |

Recommend option 1 unless the PDF really is a different deliverable. In every case, report the current drift with counts.

## Pages generated from data

When reference content already exists as structured data (command JSON, config parameter lists, GUC tables, SQL function signatures), generate the pages instead of hand-writing them:
- The source of truth is the data file, and the page is a build artifact (a macros template, a `gen-files` plugin, or a pre-build script).
- Generated pages get a banner or a comment saying "generated, edit X". The inventory can then exclude them with `--type-rule '...=reference'`.
- Diff the coverage: items in the data with no page, and pages with no item. That is a coverage metric (metrics.md).

## Enforcing the model

Write a small validator (Python, run in CI) that reads front matter and fails on missing required fields, values outside the enum, or tags not in the vocabulary. Run the inventory in CI and fail on `links_broken > 0`, `nav_missing_files`, or new orphans. Leave prose checks to Vale. The model check is structural, so keep the two separate.
