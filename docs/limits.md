---
title: "Known limits"
description: "What docs-health heuristics can miss: topic type guesses, ages, unchecked links, duplicates, nav parsing and coverage."
---

- Topic types are guessed from structure (numbered steps, verb headings, tables). Spot-check them, or pin them with `--type-rule`.
- Age is time since the last non-bulk commit. It isn't a review date, and renames aren't followed.
- Links built from variables (`{{ ... }}`), absolute site URLs, anchors and external links aren't checked.
- Duplicates are verbatim paragraphs only. Near-duplicates and overlapping tables are missed.
- Nav parsing in `inventory.py` is MkDocs-only. For valkey-doc's `nav.yml`, use `scripts/checks/valkey_nav.py`.
- Coverage checks presence, not correctness: a page that exists and mentions an item may still be wrong. Mentions count only in code formatting (backticks, fenced code, bold).
