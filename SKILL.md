---
name: "docs-health"
description: Health checks for docs-as-code sets. Use it to audit or restructure a docs nav or IA (merge/split/move pages, topic types, front matter, reuse), to measure a doc set (inventory, stale pages, orphans, broken links, nav drift, duplication, analytics joins), to compare two doc sets (two branches, a local checkout vs GitHub, two repos), to check docs against code (undocumented commands or config options, pages for removed items, missing Reply sections, deprecated names still taught), and to run a metadata and SEO pass (titles, meta descriptions, H1s, canonicals, structured data). Outputs CSVs, a Markdown report and a self-contained HTML report, and ends with a separate reviewer agent. Trigger for MkDocs or other Markdown doc repos the user names, even for "is our structure OK", "what pages are stale", "what is missing on this branch", "what is undocumented" or "check our titles and descriptions". Not for line-editing prose.
---

# Docs health

Treat a doc set as a dataset. Measure it, design from the data, then change it in a way that keeps the URLs working.

The skill exists because architecture problems don't show up in individual pages. Nav that has drifted between an HTML config and a PDF config, orphaned pages, five copies of the same install paragraph, and a "Get started" section that is four levels deep are all invisible when you read pages one at a time. They are obvious in a table.

## Scope: only what the user named

Analyze only the repos, branches, and local paths the user named in this request. Don't add other branches, versions, sibling repos, or "related" doc sets to widen the picture. If you think another source would change the answer, say so in one line and let the user decide.

A code repo (command definitions, config source, API source) is a source like any other: use it only when the user names it or approves it. Docs builds often declare their code inputs (e.g. the valkey.io website build reads `valkey-io/valkey`). That makes it a good candidate to suggest, not permission to clone it.

If no source is clear ("is our structure OK?" with no repo or path), ask which repo and branch before running anything. Don't pick one from memory, an earlier conversation, or `references/repos.md`. That file only describes layouts; it is not a list of things to scan.

## Single or compare

Decide this first. It sets which script you run.

- **Single**: one repo or branch ("audit valkey-doc", "what's stale in PPG"). Use the workflow below.
- **Compare**: two sources ("unstable vs main", "my local vs unstable", "18 vs 19", "our docs vs theirs"). Read `references/compare.md` and run `scripts/compare.py`. It runs the inventory on both sides, so the rest of this file still applies to each side.

If the user names two sources, it is compare. If it is unclear which side is the reference, A is the reference (usually upstream, main, or the newer release) and B is the one being checked. Say which way round you took them.

## Pick the topic

| The ask is about… | Topic | Read |
|---|---|---|
| nav/tree, where X belongs, merge/split/move pages, landing pages, cross-repo or cross-version consistency, restructure plans | IA | `references/ia.md` |
| topic types (Diátaxis/DITA/modular), page templates, front matter fields, tags, snippets/variables reuse, single-sourcing HTML+PDF, generating pages from data | Content model | `references/content-model.md` |
| inventory, freshness, orphans, broken links, duplication, coverage, KPIs, analytics/Search Console joins, prioritizing what to fix | Metrics | `references/metrics.md` |
| docs vs code (any project, via a YAML profile; Valkey built in): undocumented commands/options/functions, pages for removed items, missing required sections, deprecated items still used, menu coverage of code groups | Coverage | `references/coverage.md` |
| page titles, meta descriptions, H1s, canonicals for versions, structured data (JSON-LD), search snippets, Search Console findings, writing for AI retrieval (GEO) | Metadata & SEO (step 8) | `references/google-metadata-rules.md`, `references/docs-frontmatter-patterns.md`, `references/seo-sources.md` |

Most real asks span two topics. A restructure, for example, needs metrics to justify it and a content model to keep it coherent. Read every reference that applies. `references/repos.md` has known layouts of some Percona and Valkey repos. Read it when the user names one of them, and never use it to choose what to scan.

## Workflow

### 1. Inventory before opinions

Run the inventory on the repo before you say anything about structure:

```bash
git -C REPO fetch --unshallow 2>/dev/null   # ages and commit counts are wrong on shallow clones
python scripts/inventory.py REPO --out inv/   # auto-detects mkdocs*.yml; INHERIT is resolved
```

Useful flags: `--config` (repeatable) to choose configs, `--docs-dir` for non-MkDocs repos, `--type-rule 'commands/*.md=reference'` when path conventions define types, and `--bulk-commit-files N` (default 30) and `--ignore-commit-subject REGEX` (e.g. version-bump sweeps) so mass edits don't count as maintenance.

It writes `pages.csv` (one row per page: nav placement per config, URL, words, headings, code blocks, admonitions, tables, links in/out/broken, snippets, variables, front matter keys, topic-type guess + signals, last meaningful commit, age), `nav.csv`, `links.csv`, `duplicates.csv`, `summary.json`, `summary.md`.

Then use pandas or plain Python on the CSVs to answer the actual question. Don't estimate counts in prose. If a number appears in your answer, it came from a file or a command you can name.

### 2. Verify before reporting

The script is heuristic. Before a finding goes in the report, open the files behind it.
- **Topic types** are guesses from structure (numbered steps, verb headings, tables). Spot-check at least five pages, including some from every type you plan to talk about. If a path convention is reliable, add a `--type-rule` and rerun.
- **Orphans** can be intentional: pages reached by a direct link, `not_in_nav`, auto-appended snippets, or includes the parser doesn't know about. Grep the config and the repo before calling a page dead.
- **Broken links**: links built from variables (`{{ ... }}`) and absolute site links are skipped. Say that this case is out of scope rather than claiming zero.
- **Age** is time since the last non-bulk commit to the file. It is not the time since someone verified the content. Say so whenever freshness drives a recommendation.

### 3. Analyze with the topic reference

Follow the checklist in the relevant reference. Compare against the user's actual constraints, such as who reads it, the release cadence, which configs build which outputs, and what is versioned. Don't compare against an idealized docset.

### 4. Recommend with evidence and trade-offs

Each finding needs:
- **Evidence**: a count plus 2–3 example paths.
- **Impact**: who is hurt and how (findability, trust, maintenance cost, build or PDF breakage).
- **Fix**: concrete. A nav YAML snippet, a mapping row, a field definition, or a script.
- **Pros / cons** of the fix, including what it costs to maintain. Give alternatives when there is a real choice.
- **Effort and reversibility**. Moving URLs is expensive and hard to undo. Adding front matter is cheap.

Rank the findings by impact ÷ effort. Lead with the fixes that are cheap and high-impact.

### 5. Changes that move pages

Any move, rename, merge, or delete requires a mapping table plus redirects. It also requires updating the nav in *every* config that lists the page and a post-change inventory diff. The procedure is in `references/ia.md` → "Restructure procedure". Don't hand over a new tree without the migration path.

### 6. Deliver

Data plus a short report. Default report shape:

```markdown
# <Doc set>: architecture review
## Summary            ≤5 bullets, each with a number
## Findings           | # | Finding | Evidence | Impact | Fix | Effort |
## Recommendations    one subsection each: change, pros, cons, alternative
## Proposed structure nav YAML (IA asks only), annotated with moves
## Migration          mapping CSV + redirect_maps + steps (if anything moves)
## Data & caveats     files produced, commands run, heuristics, shallow history, etc.
```

Keep it short. The reader is a technical writer who knows MkDocs, Diátaxis, and DITA, so don't explain those. Spend the words on what is specific to this doc set. Put the CSVs next to the report so the user can re-slice them.

Save the report as `report.md` (or `<topic>-report.md`) in the output folder, then compile everything in that folder into one HTML page and deliver it with the Markdown and CSVs:

```bash
python scripts/html_report.py inv/ --title "<Doc set>: architecture review"        # writes inv/report.html
python scripts/html_report.py cov/ inv/ --out review.html --title "..."            # several folders in one page
```

The page has every `.md` in the folder rendered (the main report first, then `optimizations.md`, then the rest) and every `.csv`/`.tsv` as a sortable, filterable table. It has no external assets and uses ES5 script only, so it opens offline in any browser. Build it again after step 7 so the optimizer's report is included.

### 7. Optimization review (separate agent)

After any scan (single or compare), get a second opinion from an agent that didn't produce the scan, so the work isn't grading itself:

- **With an Agent/Task tool:** spawn one subagent with the prompt in `agents/optimizer.md`. Fill in the scan output folder(s), the source(s), the user's original ask, and your report. Don't pass your reasoning beyond the report. Run it after your report is done. It can run in the background while you deliver your report.
- **Without one:** do the same review yourself as a separate pass after delivering the report. Follow `agents/optimizer.md` and label the result as a self-review.
- **Skip it** when the user says so ("no review", "just the numbers") or when the scan was a quick lookup rather than an audit.

Deliver the optimizer's report as written, under its own heading, after yours. If it disagrees with your report, say where in one line and don't argue it away. If the agent can't write files, save its returned text as `optimizations.md` next to the scan output. Then rerun `scripts/html_report.py` on the folder so the HTML page includes the review.

### 8. Metadata & SEO pass (separate, optional)

This is a second pass with its own report. Run it when the user asks about titles, descriptions, search visibility, SEO or GEO. After an audit or compare, offer it in one line instead of running it unasked. Keep it out of the architecture report: the fixes are different, and so is who makes them (often the site template, not the content).

1. **Check the build first.** Read the site's head template and one live page, and confirm which source fields reach `<title>`, `<meta name="description">`, `og:*` and `rel="canonical"`. A broken chain (e.g. the description never emitted) outranks every per-page finding. Procedure: `references/docs-frontmatter-patterns.md` → "Check the build".
2. **Run the check** on the pages that carry their own metadata, with the rendered title format:
   ```bash
   python scripts/metadata_check.py REPO --glob 'topics/*.md' --out meta/ \
     --title-template '<Site prefix> · {title}'
   ```
   It writes `metadata.csv` and `metadata_summary.md`: missing or duplicate titles and descriptions, one-word (UI-label) titles, body H1s next to a front-matter title, title/H1 mismatches, shared title prefixes, and lengths. Lengths are heuristics, because Google sets no limit, so report them as info.
3. **Apply the rules** in `references/google-metadata-rules.md` (Google Search Central: titles, rewrite triggers, snippets, robots controls, canonicals). Use `references/docs-frontmatter-patterns.md` for docs-specific practice (intent-first titles, version canonicals, front matter template, JSON-LD, GEO). Where a platform guide conflicts with Google, Google wins. Say so when it matters.
4. **Verify** as in step 2: open the pages behind each issue type. Generated pages (command references) get their titles and descriptions from templates, so judge the template, not each page.
5. **Report** in `meta/seo-report.md`, using the step 6 shape, plus:
   - a **Build** section (what reaches the HTML, and what doesn't);
   - a **Rewrites** table for the 10–20 highest-value pages only (current title or description → proposed, with the reason). Rank by traffic when analytics are available, otherwise by nav prominence. Write intent-first titles and specific, varied descriptions; never keyword lists;
   - template fixes (site prefix, description fallback, JSON-LD, canonicals) as code snippets, separate from content fixes.
6. Build the HTML with `scripts/html_report.py meta/`.

Sources: cite the official pages listed in `references/seo-sources.md`. The books there are background for the user. Don't attribute rules or quotes to them.

If the user wants ongoing tracking rather than a one-off, offer a dashboard built from `pages.csv`, or a CI check (see `references/metrics.md` → "Automating"). `metadata_check.py` can run in CI the same way, failing on `error` issues.

## Analytics

When the user has GA4, Search Console, or another export, join it to the inventory:

```bash
python scripts/join_analytics.py inv/pages.csv export.csv --out inv/joined.csv
```

URLs are normalized and versioned prefixes are matched by suffix. Rows with no matching page go to `unmatched.csv`. Those are URLs people still hit that no longer exist, so they are redirect candidates. If the user only has traffic data and wants priorities, use the traffic × issue approach in `references/metrics.md`.

## Boundaries

- This skill doesn't line-edit wording. If the user wants prose review of specific pages, do that separately. The exception is step 8's rewrites table: proposed titles and descriptions for a ranked set of pages, given as suggestions, not applied.
- Don't edit the repo unless asked. When asked, work on a branch and keep each change type in its own commit: nav, moves plus redirects, front matter, snippet extraction.
- Claims about how a tool behaves (a mkdocs plugin option, GA4 field names) change over time. Check the plugin docs or the repo's `requirements.txt` version before relying on one.
