# docs-health

**Documentation: https://andriciuc.github.io/docs-health/**

A Claude skill and set of GitHub workflows that treat a docs-as-code set as a dataset. They inventory every page, measure freshness, links, nav coverage and duplication, check the docs against the code they describe, and audit SEO metadata. The numbers then become a ranked review, which a separate reviewer agent checks.

In short: a check-up for documentation. It reads your doc pages and the code they describe, then lists what's missing, outdated, broken or hard to find. A person decides what to fix.

It's built for MkDocs and plain-Markdown doc repos. The scripts also work without Claude.

## Quick start

**As a Claude skill** (Claude Code):

```bash
git clone https://github.com/Andriciuc/docs-health.git ~/.claude/skills/docs-health
```

Then ask: `/docs-health audit valkey-io/valkey-doc main for gaps and stale pages`. For the Claude apps, see [Get started](https://andriciuc.github.io/docs-health/get-started/).

**Docs vs code from the command line** (built-in Valkey profile):

```bash
pip install -r requirements-run.txt   # PyYAML, pinned
python scripts/profile_coverage.py valkey --code ../valkey --docs ../valkey-doc --out cov
python scripts/html_report.py cov          # cov/report.html
```

**As a GitHub workflow** (monthly, your own pairs): see [GitHub workflows](https://andriciuc.github.io/docs-health/workflows/).

## Documentation

| Page | What's there |
|---|---|
| [Get started](https://andriciuc.github.io/docs-health/get-started/) | Install, requirements, repository layout |
| [Using it with Claude](https://andriciuc.github.io/docs-health/using-with-claude/) | Example prompts and the steps of a run |
| [Audit and compare](https://andriciuc.github.io/docs-health/checks/audit-and-compare/) | Inventory, comparisons, analytics joins |
| [Docs vs code](https://andriciuc.github.io/docs-health/checks/docs-vs-code/) | Coverage with profiles |
| [Write a profile](https://andriciuc.github.io/docs-health/checks/write-a-profile/) | Make coverage work for your project |
| [Metadata and SEO](https://andriciuc.github.io/docs-health/checks/metadata-seo/) | Titles, descriptions, H1s |
| [HTML report](https://andriciuc.github.io/docs-health/checks/html-report/) | One shareable page per scan |
| [GitHub workflows](https://andriciuc.github.io/docs-health/workflows/) | docs-coverage and docs-compare, inputs, examples |
| [Known limits](https://andriciuc.github.io/docs-health/limits/) | What the heuristics can miss |
| [Security](SECURITY.md) | What the workflows can access, and how to report a problem |

The site's source is in [`docs/`](docs/). Edit it there; `pages.yml` publishes every merge to `main`.

## Contributing and license

Issues and PRs are welcome. Every PR runs these checks, and a finding fails the check on the PR:

- **ruff**: lints the Python for bugs and insecure patterns.
- **Tests**: the unit tests, including tests for the hardening. Fails if line coverage drops below 80%.
- **pip-audit**: checks the pinned packages for known CVEs.
- **zizmor**: static security analysis of the workflows.
- **Docs build**: a strict MkDocs build plus docs-health's own metadata check.
- **Smoke runs**: both reusable workflows run against valkey-doc and valkey.

Dependabot opens one PR a month to bump the pinned versions. More in [Contributing](https://andriciuc.github.io/docs-health/contributing/).

Apache License 2.0. See [LICENSE](LICENSE).
