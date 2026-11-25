#!/usr/bin/env python3
"""Check page metadata in Markdown sources: titles, descriptions and H1s.

Usage:
  python metadata_check.py DOCS_ROOT [--glob 'topics/*.md' ...] [--out DIR]
                           [--title-key title] [--desc-key description]
                           [--title-max 60] [--desc-min 70] [--desc-max 160]
                           [--prefix-min 3] [--short-title-words 1]
                           [--title-template 'Valkey Documentation · {title}']

Rules come from references/google-metadata-rules.md and
references/docs-frontmatter-patterns.md. Length limits are heuristics: Google
sets none and truncates to fit the device, so they're reported as info.

Per page:
  error  missing_title           no front-matter title and no H1
  error  duplicate_title         same title (case-insensitive) as another page
  warn   missing_description     no description key
  warn   duplicate_description   same description as another page
  warn   short_title             <= --short-title-words words: likely a UI label ("Hashes", "Overview")
  warn   body_h1_with_title      front-matter title plus an H1 in the body (two main titles)
  warn   multiple_h1             no front-matter title and more than one H1
  info   title_h1_mismatch       front-matter title and first H1 differ
  info   long_title              rendered title longer than --title-max characters
                                 (rendered = --title-template applied, e.g. the site's prefix)
  info   short_description / long_description   outside --desc-min..--desc-max
  info   shared_prefix           title starts with a prefix shared by >= --prefix-min titles
                                 ("Valkey Search - "): micro-boilerplate candidate

Headings inside fenced code blocks are ignored. A UTF-8 BOM is tolerated.

This reads sources only. Whether the build actually emits the title and
description into <title> and <meta name="description"> is a separate check:
read the site's head template and look at one live page (see
references/docs-frontmatter-patterns.md, "Check the build").

Writes to --out (default ./docs-metadata):
  metadata.csv           one row per page: title, lengths, description, h1 count, issues
  metadata_summary.md    counts per issue and the pages behind each

Stdlib + PyYAML (optional: without it, simple `key: value` front matter is read).
"""
import argparse, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

FENCE = re.compile(r"^\s*(```|~~~)")
H1 = re.compile(r"^#\s+(.+?)\s*#*\s*$")
SEPARATORS = (" - ", " – ", " — ", ": ", " | ")  # noqa: RUF001 - en dash is a real title separator
SEVERITY = {
    "missing_title": "error", "duplicate_title": "error",
    "missing_description": "warn", "duplicate_description": "warn", "short_title": "warn",
    "body_h1_with_title": "warn", "multiple_h1": "warn",
    "title_h1_mismatch": "info", "long_title": "info", "short_description": "info",
    "long_description": "info", "shared_prefix": "info",
}


# Same rule as MkDocs (mkdocs/utils/meta.py): "---" on the first line, closed by a line that is
# exactly "---" or "..." (trailing spaces allowed). A "----" rule or "---x" line doesn't close it.
FRONT_MATTER = re.compile(r"\A-{3}[ \t]*\n(.*?\n)?(?:\.{3}|-{3})[ \t]*(?:\n|\Z)", re.S)


def front_matter(text):
    m = FRONT_MATTER.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1) or "", text[m.end():]
    if yaml:
        try:
            data = yaml.safe_load(raw) or {}
            return (data if isinstance(data, dict) else {}), body
        except yaml.YAMLError:
            pass
    data = {}
    for line in raw.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            data[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return data, body


def h1s(body):
    out, infence = [], False
    for line in body.splitlines():
        if FENCE.match(line):
            infence = not infence
            continue
        if not infence:
            m = H1.match(line)
            if m:
                out.append(m.group(1))
    return out


def norm(s):
    return " ".join(str(s or "").split())


def prefix(title):
    for sep in SEPARATORS:
        if sep in title:
            return title.split(sep, 1)[0] + sep
    return ""


def run(root, globs, title_key, desc_key, title_max, desc_min, desc_max, prefix_min,
        short_words=1, template="{title}"):
    root = Path(root)
    pages = []
    seen = set()
    for g in globs:
        for f in safeio.files(root, g):
            rel = f.relative_to(root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            text = safeio.read_text(f)
            fm, body = front_matter(text)
            heads = h1s(body)
            fm_title = norm(fm.get(title_key))
            title = fm_title or (norm(heads[0]) if heads else "")
            desc = norm(fm.get(desc_key))
            rendered = template.replace("{title}", title) if title else ""
            pages.append({"path": rel, "title": title, "title_source": "front matter" if fm_title else ("h1" if heads else ""),
                          "rendered_title": rendered, "title_len": len(rendered), "description": desc, "desc_len": len(desc),
                          "h1_count": len(heads), "first_h1": norm(heads[0]) if heads else "", "_fm_title": fm_title})
    titles = Counter(p["title"].lower() for p in pages if p["title"])
    descs = Counter(p["description"].lower() for p in pages if p["description"])
    prefixes = Counter(prefix(p["title"]) for p in pages if prefix(p["title"]))
    for p in pages:
        issues = []
        t, d = p["title"], p["description"]
        if not t:
            issues.append("missing_title")
        else:
            if titles[t.lower()] > 1:
                issues.append("duplicate_title")
            if len(t.split()) <= short_words:
                issues.append("short_title")
            if p["title_len"] > title_max:
                issues.append("long_title")
            pre = prefix(t)
            if pre and prefixes[pre] >= prefix_min:
                issues.append("shared_prefix")
        if not d:
            issues.append("missing_description")
        else:
            if descs[d.lower()] > 1:
                issues.append("duplicate_description")
            if len(d) < desc_min:
                issues.append("short_description")
            if len(d) > desc_max:
                issues.append("long_description")
        if p["_fm_title"] and p["h1_count"]:
            issues.append("body_h1_with_title")
            if p["first_h1"].lower() != p["_fm_title"].lower():
                issues.append("title_h1_mismatch")
        if not p["_fm_title"] and p["h1_count"] > 1:
            issues.append("multiple_h1")
        p["issues"] = ";".join(issues)
        p["worst"] = min((SEVERITY[i] for i in issues), key=["error", "warn", "info"].index) if issues else ""
    return pages, prefixes


def write(pages, prefixes, out, root, prefix_min):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cols = ["path", "title", "title_source", "rendered_title", "title_len", "description", "desc_len", "h1_count", "first_h1", "worst", "issues"]
    with open(out / "metadata.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(pages)
    by_issue = defaultdict(list)
    for p in pages:
        for i in filter(None, p["issues"].split(";")):
            by_issue[i].append(p)
    md = [f"# Metadata: {root}", "", f"{len(pages)} pages checked.", "",
          "| severity | issue | pages |", "|---|---|---|"]
    order = sorted(by_issue, key=lambda i: (["error", "warn", "info"].index(SEVERITY[i]), i))
    md += [f"| {SEVERITY[i]} | {i} | {len(by_issue[i])} |" for i in order]
    shared = [(k, n) for k, n in prefixes.most_common() if n >= prefix_min]
    if shared:
        md += ["", "## Shared title prefixes", ""] + [f"- `{k}` — {n} titles" for k, n in shared]
    for i in order:
        if SEVERITY[i] == "info" and i != "title_h1_mismatch":
            continue
        rows = by_issue[i]
        md += ["", f"## {i} ({len(rows)})", ""]
        for p in rows[:40]:
            extra = f" — H1: `{p['first_h1']}`" if i in ("title_h1_mismatch", "body_h1_with_title") else ""
            md.append(f"- `{p['path']}`: {p['title'] or '(no title)'}{extra}")
        if len(rows) > 40:
            md.append(f"- … {len(rows) - 40} more in metadata.csv")
    (out / "metadata_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--glob", action="append", default=[], help="pages to check (default **/*.md)")
    ap.add_argument("--out", default="docs-metadata")
    ap.add_argument("--title-key", default="title")
    ap.add_argument("--desc-key", default="description")
    ap.add_argument("--title-max", type=int, default=60)
    ap.add_argument("--desc-min", type=int, default=70)
    ap.add_argument("--desc-max", type=int, default=160)
    ap.add_argument("--prefix-min", type=int, default=3)
    ap.add_argument("--short-title-words", type=int, default=1)
    ap.add_argument("--title-template", default="{title}",
                    help="how the site renders <title>, e.g. 'Valkey Documentation · {title}'")
    a = ap.parse_args()
    pages, prefixes = run(a.root, a.glob or ["**/*.md"], a.title_key, a.desc_key,
                          a.title_max, a.desc_min, a.desc_max, a.prefix_min,
                          a.short_title_words, a.title_template)
    write(pages, prefixes, a.out, a.root, a.prefix_min)
    c = Counter(p["worst"] for p in pages)
    sys.stderr.write(f"{len(pages)} pages: {c.get('error', 0)} with errors, {c.get('warn', 0)} with warnings; wrote {a.out}/\n")
