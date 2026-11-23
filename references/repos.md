# Known repo layouts

Verify against the checkout. These were observed in November 2026 and can change.

## percona/postgresql-docs (PPG)
- Default branch is the current major (e.g. `19`). Other majors live on their own branches and are published with `mike` (version provider in `extra.version`).
- Configs: `mkdocs-base.yml` (parent: theme, plugins, markdown_extensions, its own nav), `mkdocs.yml` (HTML: `INHERIT: mkdocs-base.yml`, sets `site_url`, **redefines nav**), `mkdocs-pdf.yml` (`INHERIT`, PDF build). Expect nav drift between base/pdf and the HTML nav.
- `use_directory_urls: false`, so URLs are `…/page.html`.
- Variables: `variables.yml` via `macros` `include_yaml` (`pgversion`, `pgsubversion`, `dockertag`, `pspgversion`, release dates…).
- Snippets: `pymdownx.snippets` `base_path: ["snippets"]` with `auto_append` of a banner, so snippet paths resolve from `snippets/`, not from the page.
- Sections: Get started (numbered journey), Extensions, Solutions (HA, authentication…), Upgrade, Troubleshooting, Release notes.

## percona/pg_tde
- Docs live in `documentation/` (`documentation/mkdocs.yml`, `docs_dir` = `documentation/docs`). Run the inventory on the repo root and it auto-detects them.
- `site_url: https://docs.percona.com/pg-tde/`, `use_directory_urls: false`, mike versioning.
- Many release-notes pages, so exclude them from size and age outliers.

## percona/pg_stat_monitor
- The code repo has almost no docs. The documentation is in `percona/pgsm-docs`, so clone that instead.

## valkey-io/valkey-doc
- Branches (Nov 2026): `main` plus release/topic branches (e.g. `update-docs-9.1.0-rc1`); no `unstable`. `unstable` is the server repo `valkey-io/valkey`. Check with `git ls-remote --heads` before comparing.
- Not MkDocs. Plain Markdown rendered by the valkey-io.github.io site build. Run the inventory with `--docs-dir .` (auto when no mkdocs config) and `--type-rule 'commands/*.md=reference'`.
- `commands/*.md` (one page per command), `topics/*.md` (guides and concepts), plus `clients/`, `libraries/`, `modules/` (data-like entries) and `groups.json`/`languages.json`.
- Menu: `nav.yml` (added in #513, Nov 2026) plus `modules-nav/*.yml` for module topics. The schema isn't MkDocs (`id`, `title`, `landing`, `topics` as names or `{topic, title, commands}`), so the inventory doesn't parse it and reports orphans as 0 regardless. Check menu coverage with a short script: every `topics/*.md` except `index` listed exactly once, and every `landing` and uppercase command reference resolving to a file.
- `topics/index.md` is a second, hand-written entry point used by the man pages and `make html`. Compare it against `nav.yml` case-sensitively (`ARM.md`, `RDMA.md`), and measure reachability in hops through `links.csv` rather than direct links only.
- Some topics start with a UTF-8 BOM (`hashes`, `lists`, `sets`, `strings`, `geospatial`).
- `topics/modules-api-ref.md` is generated from `src/module.c`. Exclude it from size, age and duplicate findings.
- Command metadata (arguments, complexity, ACL categories) comes from the server repo's command JSON. Treat that as the data source for coverage checks.
