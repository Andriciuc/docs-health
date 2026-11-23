# Docs metadata patterns: front matter, versions, structured data, AI retrieval

Docs-specific practice from documentation platforms, checked November 2026. These are vendor guides. Where one conflicts with Google's rules (`google-metadata-rules.md`), Google's rules win, and the conflict is noted below.

Sources:
- Read the Docs, SEO for documentation projects: https://docs.readthedocs.com/platform/stable/guides/technical-docs-seo-guide.html
- Redocly, SEO best practices for documentation: https://redocly.com/blog/seo-best-practices-documentation
- GitBook, GEO guide: https://gitbook.com/docs/guides/seo-and-llm-optimization/geo-guide
- Mintlify, how to improve documentation SEO: https://www.mintlify.com/docs/guides/seo
- Mintlify, SEO configuration reference: https://www.mintlify.com/docs/optimize/seo
- Schema.org TechArticle: https://schema.org/TechArticle and APIReference: https://schema.org/APIReference

## Contents
- Docs failure modes
- Titles and headings
- Descriptions
- Front matter template
- Check the build
- Versions, moves and indexing
- Structured data (JSON-LD)
- AI retrieval (GEO)
- Measuring

## Docs failure modes

These are the problems doc sets have that marketing sites don't:

| Failure | Signal in the repo | Source |
|---|---|---|
| UI-label titles ("Authentication", "Configuration") | One- or two-word titles that match nav labels | Mintlify, Redocly |
| Micro-boilerplate titles | Many titles share a long prefix ("Valkey Search - ") | Google |
| Missing or template descriptions | No `description`, or the same text on many pages | Google, Read the Docs |
| Body H1 plus front-matter title | `h1_count` ≥ 1 on pages with a `title` key | Mintlify |
| Old versions outranking current | No canonical from versioned pages to current | Redocly, Read the Docs |
| Orphan pages | Not in nav, no inbound links | Read the Docs, Mintlify |
| Moved pages without redirects | Renames in git history, 404s in Search Console | Read the Docs, Redocly |

The first four come from the source files: `scripts/metadata_check.py` reports them. The others come from the inventory (`inventory.py`) and analytics (`join_analytics.py`).

## Titles and headings

- Write titles the way people search, not the way the UI labels things: "How to authenticate API requests", not "Authentication" (Mintlify).
- Each title should be unique and descriptive, for example "Overview of API authentication" rather than "Overview" (Redocly).
- Mintlify suggests about 50–60 characters, with the main term near the start. Google sets no limit but truncates. Treat 60 as "check the front of the title carries the meaning", not as a hard rule.
- Have one H1, generated from the front-matter `title`. Body headings start at H2 (Mintlify).
- Headings phrased as an intent or question match search queries and AI prompts better: "How authentication works" rather than "Authentication" (Mintlify, GitBook).
- Reference pages: give each endpoint, command and error code its own page with a specific title, because developers search for exact names and error strings (Redocly).

## Descriptions

- Describe what the reader can do or learn on this page, in active voice (Mintlify).
- Read the Docs suggests 150–300 characters, expecting truncation around 150. Mintlify suggests 130–160. Use roughly 70–160 as the flag range: shorter is usually too thin, and longer gets truncated.
- Descriptions affect how a result looks, not its ranking, and search engines may still pick a passage from the page instead (Read the Docs, Google).

## Front matter template

A neutral template that maps onto MkDocs (Material), Mintlify, Redocly and Hugo-style generators. Use only the keys the site build actually reads: check the theme or plugin first.

```yaml
---
title: "Configure TLS for replication"          # unique, intent-first; becomes <title> and the single H1
description: "Enable TLS between primary and replicas in Valkey 9.x: certificates, config options and how to verify the connection."
# optional, only if the build uses them:
canonical: "https://example.com/docs/latest/tls-replication/"   # per-page override; usually generated
keywords: ["tls", "replication"]                 # most engines ignore this; keep for site search only
og:image: "/img/social/tls.png"                  # social preview; many platforms generate one
last_reviewed: 2026-11-23                        # freshness metadata that isn't a commit date
noindex: false                                   # true for drafts and deprecated stubs
---
```

Notes:
- Mintlify derives `og:title`/`og:description` and the Twitter card fields from `title`/`description`, and builds the canonical from the page URL. Other generators are similar, so per-page overrides are rarely needed.
- `last_reviewed` gives the freshness signal git history can't: the inventory's "age" is the last commit, not the last review.

## Check the build

Source metadata only counts if the build puts it into the HTML. Before reporting source-level findings, confirm the chain once per site:
1. Read the head template, and find what fills `<title>`, `<meta name="description">`, `og:*` and `rel="canonical"`.
2. Check that the variables it reads are the ones the source sets. Sites that pull docs from another repo, with stub pages plus a loader, often read the stub's front matter instead of the loaded file's.
3. Open one live page and confirm each tag is present, with the expected text (WebFetch can report head metadata; say when it can't).

Example (valkey.io, November 2026): `templates/includes/head.html` builds `<title>` from the loaded valkey-doc `title` (`Valkey Documentation · {title}`), but the description tag reads `page.description` from the generated stub. Stubs have no description, so the valkey-doc `description` of every topic is dropped, and `https://valkey.io/topics/sets/` ships with no meta description. One template line fixes it, which is worth more than rewriting 87 descriptions.

Record the rendered title format and pass it to `metadata_check.py --title-template` so length checks match what search engines see.

## Versions, moves and indexing

- Point the canonical of every older version at the current version of the same page, and add a banner on old versions linking to the newest docs (Redocly). Read the Docs does this automatically for the default version.
- When a page moves, add a redirect and update internal links (Read the Docs). Use 301s (Redocly).
- Read the Docs suggests `robots.txt` to stop crawling of unsupported versions. Google and Redocly point out that `robots.txt` doesn't remove URLs from the index. Use `noindex` or canonicals to keep old versions out of results, and `robots.txt` only to manage crawl load.
- Sitemaps: list only canonical, live URLs, with accurate `<lastmod>`. Leave out redirects, 404s and canonicalized duplicates (Redocly).
- Put a link checker in CI that fails or warns on broken internal links (Redocly, Read the Docs). This skill's inventory provides one.

## Structured data (JSON-LD)

Schema.org types for documentation:
- `TechArticle` (Thing › CreativeWork › Article › TechArticle). It adds `dependencies` (prerequisites, Text) and `proficiencyLevel` (Text; the expected values are "Beginner" and "Expert").
- `APIReference` (a subtype of TechArticle). It adds `programmingModel` (managed or unmanaged), `targetPlatform`, `assemblyVersion` and `executableLibraryName`. These fields suit .NET-style libraries and fit command references like Valkey's poorly. `TechArticle` is usually the better choice.
- Inherited fields worth filling: `headline`, `description`, `dateModified`, `author`, `isPartOf`, `about`.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Configure TLS for replication",
  "description": "Enable TLS between primary and replicas in Valkey 9.x.",
  "proficiencyLevel": "Expert",
  "dependencies": "Valkey 9.0 or later built with TLS support; CA and server certificates",
  "dateModified": "2026-11-23",
  "isPartOf": {"@type": "WebSite", "name": "Valkey Documentation", "url": "https://valkey.io/"}
}
</script>
```

Caveats:
- Google's Article structured data (https://developers.google.com/search/docs/appearance/structured-data/article) supports only `Article`, `NewsArticle` and `BlogPosting`; `TechArticle` isn't listed. Google recommends `headline`, `author`, `datePublished`, `dateModified` and `image`, and says markup can improve the title, image and date shown, with no guarantee. For Google, `@type: "Article"` with those fields is the documented option. `TechArticle` describes the page to other consumers (other engines, AI crawlers), not a Google feature. Choose based on the audience, and say which one you chose.
- Breadcrumb structured data helps results show the docs hierarchy (Redocly).
- Generate it in the theme template from front matter. Don't hand-write it per page.

## AI retrieval (GEO)

From GitBook's guide, for docs that AI assistants retrieve and cite:
- Keep each page to one concept, task or API area, so it splits cleanly into retrievable chunks. GitBook suggests sections of about 200–400 words.
- Keep a strict H1–H3 hierarchy with descriptive headings, which also makes anchors predictable. Question-style subheads work when they match real prompts.
- Use literal language. Define a term once and link to that definition. Spell product names the same way everywhere.
- Put short examples and request/response pairs next to the concept they illustrate. Code blocks should be runnable, with a language tag.
- Give images alt text that says what they show and why. Prefer text (Markdown, JSON) over screenshots of text.
- Keep URLs and heading anchors stable: changing slugs breaks citations and embeddings. Have one canonical URL per page.
- Publish a sitemap and consider `llms.txt` / `llms-full.txt`, plus Markdown versions of pages.
- Show author and last-updated metadata.

Much of this overlaps with good IA (`references/ia.md`) and the content model (`references/content-model.md`). Report GEO findings as structure findings, not as a separate "AI" category.

## Measuring

- Use Google Search Console and Bing Webmaster Tools for crawl errors, 404s that need redirects, and queries (Read the Docs).
- High impressions with a low click-through rate usually means the title or description needs work. A low position for important queries usually means the content does (Mintlify).
- Join the exports to `pages.csv` with `scripts/join_analytics.py` and rank fixes by traffic × issue (`references/metrics.md`).
