---
title: "HTML report"
description: "Compile a scan folder's Markdown reports and CSV data into one self-contained HTML page with sortable, filterable tables."
---

`html_report.py` compiles a scan folder into one self-contained HTML page: all Markdown reports rendered (main report first), and every CSV/TSV as a table you can sort by clicking a header and filter by typing.

```bash
python scripts/html_report.py inv/                                   # writes inv/report.html
python scripts/html_report.py cov/ inv/ --out review.html --title "Valkey docs review"
```

The page has no external assets and uses ES5 script only. It opens offline in any browser, including old ones, so you can attach it, email it or publish it as is. Tables over `--max-rows` (default 5000) are cut, with a note pointing to the full CSV. When Claude runs the skill, it builds this page at the end of every scan.
