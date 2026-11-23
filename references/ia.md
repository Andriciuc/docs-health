# Information architecture

## Contents
- Audit checklist
- Organizing schemes (pick one per level)
- Labels
- Cross-repo / cross-version structure
- Restructure procedure
- Mapping table format

## Audit checklist

Run each check against `nav.csv` / `pages.csv`. Record count + examples for every hit.

| Check | How (inventory) | Why it matters | Typical fix |
|---|---|---|---|
| Nav entry → missing file | `summary.json` per_config.nav_missing_files | Build warning or 404, and silent in non-strict builds | Fix path or remove entry |
| Nav drift between configs | `summary.json` nav_drift | The HTML and PDF (or base and override) tell different stories. Fixes get applied in one place only | Define nav once (see content-model.md → Single-sourcing) or document why they differ |
| Orphans | `orphans_not_in_any_nav` | Unfindable except by search or a deep link, and often stale | Add to nav, mark `not_in_nav` deliberately, or delete + redirect |
| Depth | `depth:<config>` max and distribution | In Material, tabs + sections + nested sections make anything at depth ≥4 hard to scan, and it collapses on mobile | Flatten, promote a section to a tab, or use section index pages |
| Thin sections | sections with 1 child in `nav.csv` | An extra click for nothing | Merge into the parent, or make the page the section index |
| Fat sections | sections with >10 direct children | Hard to scan | Group by sub-task or by type |
| Duplicate nav entries | `dup_nav_entries` | Two breadcrumbs, and the user can't tell which location is canonical | Keep one location and cross-link from the other |
| Label ≠ H1 | `nav:<config>` title vs `title` | The page name changes between the nav and the page, which hurts orientation and search snippets | Align them, with the nav label as the shorter form of the H1 |
| Mixed type in one section | `type_guess` grouped by section | A reference table in the middle of a tutorial path breaks flow | Move it to Reference and link to it |
| Inbound links = 0 and not top-level | `links_inbound` | Reachable only through the nav | Add contextual links from related tasks |
| Oversized pages | `words` > p90, or > ~2,500 | Scroll fatigue, and a page that serves several jobs | Split by task or type (content-model.md → Split rules) |
| Landing pages | `type_guess=landing`, section index pages | Sections without an overview force readers to guess | Add a short index that says what is in the section and who it is for |

## Organizing schemes

Choose one scheme per nav level and say which. Mixing schemes at the same level is the most common cause of "I don't know where this goes".

| Scheme | Top level looks like | Pros | Cons | Fits |
|---|---|---|---|---|
| Lifecycle / journey | Get started → Install → Configure → Operate → Upgrade → Troubleshoot → Reference → Release notes | Matches how admins approach a product, and new content has an obvious slot | Concepts get scattered, and cross-cutting features (security, HA) don't fit a single stage | Distributions and server products (PPG) |
| Diátaxis | Tutorials / How-to / Reference / Explanation | Keeps page types pure and gives every type a clear home | Readers don't think in types. A feature ends up split across four places | Libraries and APIs, or as the *second* level inside a feature |
| Component / feature | pg_tde / pg_stat_monitor / Patroni … | Ownership maps cleanly to teams and repos | Duplicates lifecycle tasks (install appears in every component) | Umbrella sites that link to component docs |
| Audience | Admin / Developer / Operator | Readers self-select | Most pages serve several audiences, so content gets duplicated | Rarely at the top level. Use tags instead |

Default for product docs: lifecycle at level 1, feature or topic at level 2, and type purity enforced at the page level rather than in the nav. Present the alternative when the doc set clearly looks like a library or an API reference.

Numbered sequences ("1. Install", "2. Connect") are a *journey*. Keep them short (≤5 steps), linear, and free of side branches. Put everything else in unnumbered sections.

## Labels

- Task labels: imperative verb + object ("Install on Debian"). Concept labels: noun phrase ("Key management"). Pick one form per section and keep it.
- Front-load the distinguishing word. "Via apt" / "Via yum" scans better than "Install via apt" / "Install via yum" under an "Install" section.
- Don't repeat the parent label in the child ("Install > Install overview" → "Install > Overview").
- Use product terms readers search for. Check the search-console queries if the user has them.

## Cross-repo / cross-version structure

For families of doc sets (PPG + pg_tde + pg_stat_monitor; versioned branches published with mike):
- Diff the top-level skeletons: run the inventory on each repo, then compare the depth-1 sections in `nav.csv`. Report where equivalent content lives under different labels or depths.
- Recommend a shared skeleton only where the lifecycle is actually shared. Component docs may legitimately lack sections such as an "Upgrade" chapter.
- For versioned docs, structural changes on the default branch don't fix older versions. Say which branches the change should go to, and note that redirects are per version.

## Restructure procedure

1. **Baseline**: run the inventory, keep `inv-before/`, and record the build command and whether it passes `mkdocs build --strict`.
2. **Target tree**: write the new nav as YAML. Annotate each moved entry with a comment `# from: old/path.md`.
3. **Mapping table** (format below): one row per existing page. Every page gets an action.
4. **Redirects**: for every moved, merged, or deleted page, add `old → new` to `mkdocs-redirects` `redirect_maps` (check the repo has the plugin in `requirements.txt`; if not, adding it is part of the change). With `use_directory_urls: false` the keys are `.md` paths and still map to `.html` URLs. Check against the plugin docs for the installed version.
5. **Nav in every config**: update each `mkdocs*.yml` that defines `nav`. If a child config redefines nav, decide whether it should keep doing so (see content-model.md → Single-sourcing).
6. **Links**: `git mv` the files, then fix relative links. Rerun the inventory. `links_broken` must be 0 and `nav_missing_files` empty.
7. **Build**: `mkdocs build --strict` for each config.
8. **Diff**: compare `inv-before/pages.csv` with `inv-after/pages.csv` (page count, orphans, depth distribution), and put the delta in the PR description.
9. **Analytics**: if an export is available, run `join_analytics.py` on the *old* URLs. Any URL with traffic that lacks a redirect is a blocker.

## Mapping table format

`mapping.csv`:

```
old_path,new_path,action,redirect,notes
apt.md,install/apt.md,move,yes,
docker.md,docker/docker.md,move,yes,already moved in mkdocs.yml; base still points at old path
ldap.md,,delete,yes→solutions/authentication/index.md,content merged into authentication overview
```

`action` ∈ keep, move, rename, merge, split, delete. `split` rows list each new path on its own row with the same `old_path`.
