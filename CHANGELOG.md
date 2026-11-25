# Changelog

Notable changes per release. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The `v1` tag moves to the latest 1.x release; workflows that pin `@v1` get these changes automatically.

## [Unreleased]

## [1.0.4] - 2026-11-24

### Changed
- `scripts/coverage.py` is renamed to `scripts/docs_coverage.py`. Anything that called the old path must use the new one.

### Added
- Tests for `inventory.py`, `compare.py` and `join_analytics.py`.

## [1.0.3] - 2026-11-24

### Changed
- PyYAML is installed from one pinned file (`requirements-run.txt`) in CI and in both reusable workflows.
- Dependency bumps from Dependabot.

## [1.0.2] - 2026-11-24

### Added
- PR checks: pip-audit for the pinned packages and zizmor for the workflows.
- Dependabot (monthly, grouped).

### Fixed
- docs-compare: the `history` input.

## [1.0.1] - 2026-11-24

### Security
- Scripts treat scanned repos as untrusted: files must resolve inside the scanned folder, size cap, CSV formula cells neutralized, git never prompts and times out.
- ruff (bug and security rules) runs in CI.

## [1.0.0] - 2026-11-24

First release.

- Inventory of a doc set (`inventory.py`): pages, nav, links, duplicates, freshness, topic-type guesses.
- Comparison of two doc sets (`compare.py`).
- Docs-vs-code coverage driven by YAML profiles (`profile_coverage.py`), with a built-in Valkey profile.
- Metadata and SEO check (`metadata_check.py`).
- Self-contained HTML report for any scan (`html_report.py`).
- Reusable GitHub workflows `docs-coverage` and `docs-compare`.
- Documentation site.

[Unreleased]: https://github.com/Andriciuc/docs-health/compare/v1.0.4...HEAD
[1.0.4]: https://github.com/Andriciuc/docs-health/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/Andriciuc/docs-health/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/Andriciuc/docs-health/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Andriciuc/docs-health/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Andriciuc/docs-health/releases/tag/v1.0.0
