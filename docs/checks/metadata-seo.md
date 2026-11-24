---
title: "Metadata and SEO check"
description: "Check page titles, meta descriptions and H1s in front matter against Google Search Central rules, and see what the build emits."
---

```bash
python scripts/metadata_check.py ../valkey-doc --glob 'topics/*.md' --out meta \
  --title-template 'Valkey Documentation · {title}'
```

It reads front matter (`title`, `description`; change the keys with `--title-key`/`--desc-key`) and H1s. Then it writes `metadata.csv` and `metadata_summary.md`, with issues graded `error` (missing or duplicate title), `warn` (missing or duplicate description, one-word title, body H1 next to a front-matter title, several H1s) and `info` (lengths, title/H1 mismatch, shared title prefixes). `--title-template` applies the site's title format, so length checks match the real `<title>`.

It checks sources only. Whether the site emits these fields is a separate check: `references/docs-frontmatter-patterns.md` → "Check the build".
