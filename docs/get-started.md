---
title: "Install and get started"
description: "Install docs-health in Claude Code or the Claude apps, or run its scripts on their own; requirements and repository layout."
---

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
git archive --format=zip --prefix=docs-health/ -o docs-health.skill HEAD SKILL.md README.md LICENSE SECURITY.md agents references scripts profiles docs
```

The `.skill` file is a ZIP with the skill folder at the top; the tests, fixtures and workflows stay in the repo. When you change the skill here, upload the file again: the uploaded copy doesn't follow this repo.

Renamed from `docs-architecture`: if you installed the old name, delete it from your skills so Claude doesn't see two copies. GitHub redirects the old repo URL.

**Requirements for the scripts**

- Python 3.7+
- PyYAML (`pip install pyyaml`)
- git (page ages and commit counts come from history)
- Optional: pandas, for slicing the CSVs

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
  ci.yml                  Tests, a strict docs build, and smoke runs of both reusable workflows on every PR
  pages.yml               Builds and publishes this site on every push to main
examples/
  docs-coverage.yml       Caller template: matrix of docs-vs-code pairs
  docs-compare.yml        Caller template: scheduled pairs + a one-off pair from the Run workflow form
SECURITY.md               What the workflows can access, and how to report a problem
docs/, mkdocs.yml         This documentation site (MkDocs Material), published by pages.yml
```
