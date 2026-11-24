---
title: "Contributing to docs-health"
description: "How to contribute to docs-health: the security and quality checks on every PR, how to run them locally, Dependabot, and the license."
---

Issues and PRs are welcome. Keep each change type in its own commit (scripts, references, skill instructions). For script changes, include before/after numbers from a real repo.

## Checks on every PR

A finding fails the check and shows as an annotation on the PR. Nothing is filed as an issue or a Security-tab alert.

| Check | Job | What it does |
|---|---|---|
| ruff | `unit` | Lints `scripts/` and `tests/` for likely bugs and insecure patterns: catching every error, unsafe subprocess calls, unsafe YAML loading. The rules are in `ruff.toml`; layout rules are off. |
| Tests | `unit` | Runs the unit tests with `unittest` under `coverage` and fails if line coverage of `scripts/` drops below 80%. `tests/test_hardening.py` covers symlink escapes, paths outside the repo in `mkdocs.yml`, the file size limit, CSV formula cells and profile validation. |
| pip-audit | `unit` | Checks the pinned packages in `requirements-run.txt`, `requirements-ci.txt` and `requirements-docs.txt` against public vulnerability databases. Fails on a known CVE. |
| zizmor | `zizmor` | Static analysis of the workflows and the Dependabot config: injection from workflow inputs, broad token permissions, persisted credentials, unpinned actions, wrong expression logic. Settings are in `.github/zizmor.yml`. |
| Docs build | `docs-site` | `mkdocs build --strict` (broken links, missing pages), then docs-health's own metadata check on `docs/`. |
| Workflow smoke runs | `coverage-smoke`, `coverage-profile-path-smoke`, `compare-smoke` | Runs both reusable workflows against valkey-doc and valkey. |

Run the same checks locally:

```bash
pip install -r requirements-ci.txt
ruff check scripts tests
python -m coverage run --source=scripts -m unittest discover -s tests && python -m coverage report
pip-audit -r requirements-ci.txt -r requirements-docs.txt
pipx run zizmor .github          # or: pip install zizmor
```

## Upkeep

Once a month, Dependabot (`.github/dependabot.yml`) opens one PR that bumps the pinned action SHAs and Python packages in the `requirements-*.txt` files (the reusable workflows install from `requirements-run.txt`, so callers get the same versions CI tested), skipping releases less than 7 days old. Each of those PRs goes through the checks above before you merge it.

## Hardening in the scripts

The workflows read repos the caller names, including forks, so `scripts/safeio.py` treats their content as untrusted. A file is only read if it resolves inside the folder being scanned and is under 10 MB. CSV cells that a spreadsheet would run as a formula get a leading `'`. git calls never wait for a login and have a time limit. See [Security](security.md) for the full list.

## License

Apache License 2.0. See [LICENSE](https://github.com/Andriciuc/docs-health/blob/main/LICENSE).
