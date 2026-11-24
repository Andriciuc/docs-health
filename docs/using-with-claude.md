---
title: "Using docs-health with Claude"
description: "Example prompts for audits, comparisons, coverage and SEO passes, and the steps Claude follows in every run."
---

Name the repo, and the branch or path. The skill analyzes only the sources you name and asks if none is given.

```
/docs-health audit valkey-io/valkey-doc main for gaps and stale pages
/docs-health compare percona/postgresql-docs 18 vs 19, what's missing on 18?
/docs-health propose a restructure of the Get started section in ~/work/pg_tde
/docs-health which pages should we fix first? (attach a GA4 Pages export)
```

Claude will:

1. Run the inventory (or the comparison) before giving any opinion.
2. Open the files behind each finding to verify it. The heuristics produce false positives.
3. Write a report with a summary, findings, recommendations, a proposed structure (IA asks only), migration steps (only if pages move), and data caveats.
4. Run the optimization review as a separate agent and attach its report.
5. Compile the report, the review, the summaries and the CSVs into one HTML page (`report.html`).
6. Optionally, run a separate metadata and SEO pass with its own report. It runs when you ask for it, and Claude offers it after an audit.

Say "no review" or "just the numbers" to skip step 4.
