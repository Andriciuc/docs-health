# Docs metrics

## Contents
- Metric catalog
- Prioritizing: traffic × issue
- Coverage
- Analytics sources
- Automating
- Pitfalls

## Metric catalog

Every metric needs a definition precise enough that someone else could recompute it. Give the formula and the source column.

| Metric | Definition | Source | Default flag | Caveat |
|---|---|---|---|---|
| Integrity: broken internal | count of `links.csv` status=broken | inventory | >0 | Skips links built from variables and absolute site URLs |
| Integrity: nav → missing | `nav_missing_files` per config | inventory | >0 | |
| Integrity: undefined vars | `vars_undefined` non-empty | inventory | >0 | Only when the macros plugin is on. Doesn't follow variables defined in templates |
| Findability: orphans | pages in no nav, not used as a snippet | inventory | >0 | Some are intentional |
| Findability: depth | `depth:<cfg>` distribution | inventory | ≥4 | |
| Findability: inbound links | `links_inbound` | inventory | 0 for non-top-level pages | Nav links aren't counted |
| Freshness: age | `days_since_commit` (bulk commits ignored) | git | > 365 days or older than last 2 releases | Commit ≠ review. Prefer `last_reviewed` if it exists |
| Freshness: stale-for-release | page untouched since tag X while its component changed since X | git log between tags | any | Needs a component→paths mapping |
| Maintenance: duplication | groups in `duplicates.csv` with ≥3 pages | inventory | any | Verbatim only. Near-duplicates are missed |
| Model: type purity | share of `mixed` + `task?` | inventory | >15% | Heuristic. Use `content_type` front matter once it exists |
| Model: front matter coverage | `front_matter_usage[field] / pages` | inventory | <100% for required fields | |
| Size outliers | `words` > p90 or > 2,500 | inventory | | Release notes are naturally long, so exclude them |
| Engagement | views, users, avg engagement time per page | GA4 | | Bots, consent banners and versions split the counts |
| Search demand | Search Console queries, impressions, CTR, position per page | GSC | high impressions + CTR < 2% | Points to titles/descriptions or a mismatch with intent |
| Dead demand | analytics URLs with no page (`unmatched.csv`) | join | any with traffic | Redirect candidates |
| Feedback | Material feedback widget events (helpful / not) per page | GA4 events | ratio < 0.6 with n ≥ 20 | Low n is noise |

## Prioritizing: traffic × issue

Without traffic data, rank by issue severity, and treat pages near the top of the nav as higher reach. With traffic data:

```python
import pandas as pd
df = pd.read_csv("inv/joined.csv")
df["views"] = df["Views"].fillna(0)            # column name depends on the export
df["issues"] = (df.links_broken > 0).astype(int) + (df.days_since_commit > 365).astype(int) \
             + df.type_guess.isin(["mixed"]).astype(int) + (df.words > 2500).astype(int)
df["priority"] = df.views.rank(pct=True) * df.issues
df.sort_values("priority", ascending=False).head(15)[["path","views","issues","days_since_commit","type_guess"]]
```

State the weights you used and let the user change them. The ranking is a starting point, not a verdict.

## Coverage

Coverage = documented items ÷ items that should be documented. You need an external list, for example:
- Features: release-notes entries, Jira epics/fixVersion, or a list of extensions and components in the distribution.
- Config surface: GUCs/parameters from the source (`postgresql.conf.sample`, the extension's `.control`/GUC definitions) or the command JSON in Valkey.
- Functions: from SQL install scripts.

Build the list as a CSV and match it against page titles, headings, and body text with grep. Report three lists: documented, undocumented, and documented but no longer in the source.

For anything a regex or a JSON/YAML file can list, write a profile and run `scripts/profile_coverage.py`. See `references/coverage.md`.

## Analytics sources

- **GA4** "Pages and screens" export: page path + views/users/engagement. GA4 CSV exports start with `#` comment lines, which `join_analytics.py` skips.
- **Search Console** "Pages" and "Queries" exports: clicks, impressions, CTR, position. Join Pages on URL. Queries show vocabulary for labels (ia.md → Labels).
- **On-site search**: Material puts the query into the URL as `?q=`. If GA4 site-search tracking is configured for that parameter, zero-result queries are content gaps. Verify the parameter on the live site before relying on it.
- Versioned sites (mike): the same page appears under several version prefixes. The join sums them, so if the user wants per-version numbers, split them by prefix first.

## Automating

- **CI gate** (cheap): run `inventory.py` on PRs and fail on broken links, missing nav files, undefined variables, or new orphans compared with the default branch.
- **Scheduled report**: inventory + analytics join monthly, with the top-15 priority list and deltas against last month.
- **Dashboard**: `pages.csv` is already the fact table. Useful dimensions are section, type, and age bucket. Measures: count, words, issues, views.

## Pitfalls

- Shallow clones: ages and commit counts are lower bounds, so unshallow first.
- Bulk commits (reformat, rename, link sweeps) make every page look fresh. The inventory ignores commits touching more than `--bulk-commit-files` files. Mention the threshold.
- Renames reset age unless you follow history (`git log --follow` per file). The inventory doesn't follow renames, so flag recently moved sections.
- Counting pages isn't measuring quality. Pair every count with what a reader would experience.
- Don't publish a "doc health score" that folds everything into one number without the components next to it. The components are what people act on.
