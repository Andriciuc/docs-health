---
description: "Claude skill and GitHub workflows that audit docs-as-code sets: stale pages, link and nav gaps, docs-vs-code coverage and SEO metadata."
---

# docs-health: health checks for docs-as-code

A Claude skill and GitHub workflow that treats a docs-as-code set as a dataset. It inventories every page, measures freshness, links, nav coverage and duplication, checks the docs against the code they describe and audits SEO metadata, then turns the numbers into a ranked review. A separate reviewer agent then checks that review.

It's built for MkDocs and plain-Markdown doc repos, such as Percona Distribution for PostgreSQL, pg_tde and valkey-doc. The scripts are also usable on their own, without Claude.

In short: docs-health is a check-up for documentation. It reads your doc pages and the code they describe, then lists what's missing, outdated, broken or hard to find. A person decides what to fix.

## What it does

| Ask | What you get |
|---|---|
| "Audit the structure of `owner/repo`" / "what pages are stale?" | Per-page inventory (CSV) and a short report with findings, evidence, fixes, effort, and pros/cons |
| "Compare `main` and `unstable`" / "my local checkout vs upstream" | Page-by-page diff: missing, changed, renamed, nav drift, and issues fixed or introduced |
| "Restructure the nav" / "merge these pages" | Proposed nav YAML, a mapping table, redirect maps, and a migration procedure |
| "Define topic types / front matter / reuse" | Content model: types, templates, front matter schema, snippet and variable strategy |
| "Which pages matter most?" with a GA4 or Search Console export | Analytics joined to the inventory, a traffic × issue priority list, and dead URLs that need redirects |
| "Check the docs against the code" (any project, via a profile; Valkey built in) | Commands, settings or other items with no docs, pages for removed items, missing Reply sections, deprecated names still taught, menu and group gaps |
| "Run this every month" / "compare `unstable` and the latest tag on GitHub" | Reusable GitHub workflows for coverage and compare, with your own pairs: a run summary, a `report.html` artifact, and optionally one issue per pair. See [GitHub workflows](workflows.md) |
| "Check our titles and descriptions" / "SEO pass" | A separate metadata report: whether the build emits titles and descriptions, missing, duplicate and UI-label titles, H1 problems, boilerplate prefixes, and proposed rewrites for the top pages, checked against Google Search Central rules |

Every audit ends with an **optimization review** from a second agent that didn't run the scan. It confirms or disputes findings, lists quick wins, and suggests better scan flags.

## Where to start

- [Get started](get-started.md): install the skill, or use the scripts on their own.
- [Using it with Claude](using-with-claude.md): example prompts, and what happens in a run.
- [Docs vs code](checks/docs-vs-code.md) and [Write a profile](checks/write-a-profile.md): check your docs against your code.
- [GitHub workflows](workflows.md): run it monthly or on demand, with your own pairs.
- Source: [Andriciuc/docs-health](https://github.com/Andriciuc/docs-health)
