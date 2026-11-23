# SEO and metadata sources

The rules this skill applies come from the official and platform documents below, distilled in `google-metadata-rules.md` and `docs-frontmatter-patterns.md`. The books are background reading for the user. Claude hasn't read them in this skill, so don't attribute specific rules or quotes to them. Cite a book only for the scope listed here, and point to the chapter only when the user has the book and confirms it.

## Official specifications (primary)

| Source | Use for |
|---|---|
| Google Search Central, title links: https://developers.google.com/search/docs/appearance/title-link | `<title>` rules, rewrite triggers |
| Google Search Central, snippets: https://developers.google.com/search/docs/appearance/snippet | Meta descriptions, programmatic generation |
| Google Search Central, robots meta tag: https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag | `noindex`, `nosnippet`, `max-snippet`, `data-nosnippet` |
| Google Search Central, canonicalization: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls | `rel="canonical"`, redirects, duplicates |
| Google Search Central, Article structured data: https://developers.google.com/search/docs/appearance/structured-data/article | Supported types (`Article`, `NewsArticle`, `BlogPosting`), recommended properties |
| Schema.org TechArticle: https://schema.org/TechArticle | `dependencies`, `proficiencyLevel` |
| Schema.org APIReference: https://schema.org/APIReference | `programmingModel`, `targetPlatform` |

## Documentation platform guides (secondary)

| Source | Use for |
|---|---|
| Read the Docs, SEO for documentation projects: https://docs.readthedocs.com/platform/stable/guides/technical-docs-seo-guide.html | Canonicals for versions, redirects, sitemap, meta descriptions, orphan pages |
| Redocly, SEO best practices for documentation: https://redocly.com/blog/seo-best-practices-documentation | Version canonicals, IA as internal linking, API reference pages, Core Web Vitals, sitemaps |
| GitBook, GEO guide: https://gitbook.com/docs/guides/seo-and-llm-optimization/geo-guide | Writing for AI retrieval, `llms.txt`, freshness metadata |
| Mintlify, documentation SEO guide: https://www.mintlify.com/docs/guides/seo | Intent-based titles and headings, length guidance, monitoring |
| Mintlify, SEO configuration: https://www.mintlify.com/docs/optimize/seo | Front matter keys, Open Graph fallbacks, canonicals |

These are vendor documents: some advice promotes the vendor's own features. Take the platform-neutral rule, not the product pitch.

## Books (background)

| Book | Scope |
|---|---|
| Eric Enge, Stephan Spencer, Jessie Stricchiola, *The Art of SEO*, 4th ed., O'Reilly, 2023 | Broad SEO reference, including keyword research, on-page factors, technical SEO and generative AI in search |
| Matthew Edgar, *Tech SEO Guide: A Reference Guide for Developers and Marketers Involved in Technical SEO*, Apress, 2023 | Technical SEO by topic: crawling and indexing, URL structure, content structure, structured data, sitemaps, Core Web Vitals, not-found errors, redirects |
| Anne Gentle, *Docs Like Code: Collaborate and Automate to Improve Technical Documentation*, 3rd ed., 2022 (with Diane Skwish) | Docs-as-code workflow: version control, review, CI checks, publishing |
| Eli Schwartz, *Product-Led SEO: The Why Behind Building Your Organic Growth Strategy*, Houndstooth Press, 2021 | Strategy: prioritizing what users actually need over keyword volume |

How to use the books' ideas without quoting them: prioritize pages by real user demand (Search Console queries, support tickets, error strings) over guessed keywords (Product-Led SEO), and enforce metadata rules in CI rather than in reviews (Docs Like Code). Both are already in this skill as concrete steps.
