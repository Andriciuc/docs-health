# Search engine metadata rules (Google Search Central)

Distilled from Google's own documentation, checked November 2026. Google changes these pages. Before a recommendation depends on an exact rule, open the source and confirm it.

Sources:
- Title links: https://developers.google.com/search/docs/appearance/title-link
- Snippets and meta descriptions: https://developers.google.com/search/docs/appearance/snippet
- Robots meta tag, `data-nosnippet`: https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag
- Canonicalization: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls

## Contents
- Titles
- When Google rewrites a title
- Meta descriptions and snippets
- Snippet and indexing controls
- Canonical URLs
- Audit checklist

## Titles

- Every page needs a `<title>`.
- Be descriptive and concise. Vague labels ("Overview", "Configuration") fail this rule.
- Google sets no length limit. Results are truncated to fit the device, so put the distinguishing words first.
- Don't stuff keywords. A few descriptive terms are fine; repeated words or phrases are not.
- Titles must be distinct across pages. Identical titles, and long boilerplate titles that differ in one detail, make pages hard to tell apart. Generate titles from what the page actually contains.
- Brand concisely: fuller branding on the home page only. Elsewhere, put the site name at the start or end, after a separator (`-`, `:` or `|`).
- Make the main title the most prominent text on the page (for example the first visible `<h1>`), and keep it consistent with `<title>`.
- Match the page's language and script.
- `robots.txt` doesn't keep a page out of search. It stops crawling, but the URL can still be indexed. Use `noindex` instead.

## When Google rewrites a title

Google builds the title link itself and changes it when it detects:

| Problem | What Google does | Docs example |
|---|---|---|
| Half-empty title (`| Site Name`) | Uses headings or prominent text | A template with no page title variable |
| Obsolete title (stale date or version) | Uses the visible title | "What's new in 8.0" on a page about 9.2 |
| Inaccurate title | Modifies it | A file renamed without retitling |
| Micro-boilerplate (many pages share a title) | Adds distinguishing text | Every module page titled "Valkey Search - …" with the same lead |
| No clear main title (several equal headings) | Uses the first one | Pages with several H1s |
| Language mismatch | Picks other text | English title on a translated page |
| Duplicated site name | Drops it | Site name in both the title and the result's site name |

Sources Google may use for the title link: `<title>`, the main visible title, heading elements, `og:title`, other prominent text, anchor text on the page, anchor text of links pointing to the page, and `WebSite` structured data. Changes take days to weeks to show, after a recrawl.

What this means for docs: the front-matter title, the rendered `<h1>` and the nav label should agree, and incoming link text should describe the page. A nav label like "Overview" used as anchor text everywhere weakens the title signal.

## Meta descriptions and snippets

- The snippet usually comes from page content. The meta description is used when it describes the page better than any passage, so snippets vary by query.
- Each page needs its own description. Site-level text belongs only on the home page and aggregation pages.
- With limited time, start with the most important URLs: the home page and the most visited pages.
- Include facts that help someone decide whether to click (for docs: the version, the product, what the reader can do).
- Be specific and summarize the whole page. Keyword lists, vague text and very short descriptions are less likely to be shown.
- Google sets no length limit; results are truncated to fit the device.
- Large, database-driven sites may generate descriptions programmatically, and Google encourages it. The output must read naturally, vary between pages, and use page-specific data. For docs, that means templated descriptions for command and API reference pages built from the command's summary, not one boilerplate line.

## Snippet and indexing controls

| Control | Syntax | Effect |
|---|---|---|
| `noindex` | `<meta name="robots" content="noindex">` or `X-Robots-Tag: noindex` | Keeps the page out of results |
| `nosnippet` | `<meta name="robots" content="nosnippet">` | No text snippet. Also blocks use as direct input to AI Overviews and AI Mode |
| `max-snippet:N` | `<meta name="robots" content="max-snippet:20">` | Caps snippet length. `0` acts like `nosnippet`, `-1` means no limit; an unparseable value is ignored |
| `data-nosnippet` | `<div data-nosnippet>` | Excludes that part of the page from snippets. Valid only on `span`, `div` and `section`. The HTML must be valid, because an unclosed element extends the exclusion. Don't add it with JavaScript |

Use these sparingly in docs. The usual case is `data-nosnippet` on banners ("You are viewing an old version…"), so they don't become the snippet.

## Canonical URLs

- A redirect is a strong signal, `rel="canonical"` is a strong signal, and listing a URL in the sitemap is a weak one. Combine them.
- Put `<link rel="canonical">` in the `<head>`, with an absolute URL. Give the canonical page a canonical to itself.
- Use either the HTML element or the HTTP header, not both.
- Retire duplicates with permanent redirects.
- Link internally to the canonical URL. Don't use fragment URLs as canonicals, and don't send conflicting signals.
- Don't canonicalize with `robots.txt`, `noindex` or the URL removal tool.

Versioned docs: point older versions' canonicals at the current page where it exists, unless the old version is the only one that documents the feature. In that case, give it a self-canonical.

## Audit checklist

For each page (source front matter, or the built HTML when available):
1. Is there a title, and is it unique across the site?
2. Is it descriptive: not a single generic word, and not dominated by boilerplate shared with sibling pages?
3. Do the front-matter title, the H1 and the nav label agree, with exactly one H1?
4. Is there a description, unique and specific to the page, not a template line?
5. Is the title or description out of date (old version numbers)?
6. Do old versions have a canonical to the current version, and do moved pages have redirects?
7. Are banners and other repeated boilerplate excluded from snippets?
