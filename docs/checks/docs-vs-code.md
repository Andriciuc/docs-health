---
title: "Check docs against code"
description: "Find undocumented commands and settings, pages for removed items and deprecated names still taught, using a YAML profile."
---

Code is the list of things that should be documented. A **profile** (a small YAML file) says where those things are in the code and what each one needs in the docs. `profile_coverage.py` extracts them and checks the docs. Valkey example, with `valkey` and `valkey-doc` checked out side by side:

```bash
python scripts/profile_coverage.py valkey --code ../valkey --docs ../valkey-doc --out cov
```

`valkey` is the built-in profile (`profiles/valkey.yml`). Pass a path instead to use your own: `python scripts/profile_coverage.py ./my-profile.yml --code … --docs …`.

| File | Contents |
|---|---|
| `items.csv` | Everything the profile extracted from the code |
| `coverage.csv` | One row per item: `documented`, `missing_heading`, `undocumented`, `no_page_mentioned`, `mentioned`, `not_mentioned`, `documented_elsewhere`, `skipped`; pages mentioning it; deprecated pages still using it |
| `orphans.csv` | Doc pages with no matching item (removed or renamed in the code) |
| `coverage_summary.md` | Counts and gap lists |
| `nav_coverage.csv` / `nav_summary.md` | Valkey profile only: menu coverage, unused menu entries, groups missing from `groups.json` |

Match the code branch to the release the docs target: development branches carry items that aren't released yet.
