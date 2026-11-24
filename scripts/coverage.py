#!/usr/bin/env python3
"""Check docs coverage of items extracted from code (commands, config options, functions...).

Usage:
  python coverage.py ITEMS.csv [ITEMS.csv ...] --docs DOCS_ROOT [--out DIR]
                     [--page-glob KIND=GLOB ...] [--ignore-glob GLOB ...]
                     [--mention-glob GLOB ...] [--exclude-glob GLOB ...]

ITEMS.csv: items.csv from profile_coverage.py (common format:
kind, id, name, aliases, expected_page, require_heading, skip_reason, source_path, ...).

Per item:
  skipped          skip_reason set (internal / hidden / debug); reported, not counted as a gap
  documented       expected_page exists (and has the required heading, if any)
  missing_heading  expected_page exists but has no heading starting with require_heading
  undocumented     expected_page given but missing, and no mention elsewhere
  no_page_mentioned  expected_page missing, but the item is mentioned in searched pages
  mentioned        no expected_page; the item appears in code formatting in a searched page
  not_mentioned    no expected_page; no such mention
  (profiles can add documented_elsewhere: found in a code-side reference file instead)

A mention is a backticked span or a fenced code line that equals the item's
name (or an alias) or starts with it plus a space (`maxmemory 2mb`,
`SENTINEL MASTER <name>`). Bare words in prose don't count: short names like
`port` or `dir` would match everywhere. The item's own expected_page is not
counted as a mention.

Bold spans (**SENTINEL MASTERS**) count as code spans too, since reference
lists often use them.

Items with deprecated_since: deprecated_in_use lists the pages that mention the
item without also mentioning its replacement (backticked names in replaced_by).

Reverse check (--page-glob KIND=GLOB): pages matching GLOB whose file stem is no
item id of KIND are reported in orphans.csv as no_source, or as
source_not_scanned when they also match an --ignore-glob (e.g. module
commands whose JSON you didn't extract).

Writes to --out (default ./docs-coverage):
  coverage.csv          one row per item: status, detail, pages (first 5), mentions, passthrough columns
  orphans.csv           doc pages with no source item
  coverage_summary.md   counts per kind and status, plus the gap lists

Stdlib only. Read-only on both trees.
"""
import argparse, fnmatch, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio

HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def read_items(paths):
    items = []
    for p in paths:
        items.extend(safeio.read_csv(p))
    return items


def page_index(root, globs, exclude):
    """relative path -> (headings, code spans): backticked text and fenced code lines, lowercased"""
    out = {}
    for g in globs:
        for f in safeio.files(root, g):
            rel = f.relative_to(root).as_posix()
            if rel in out or any(fnmatch.fnmatch(rel, x) for x in exclude):
                continue
            text = safeio.read_text(f)
            heads, spans = [], set()
            infence = False
            for line in text.splitlines():
                if FENCE.match(line):
                    infence = not infence
                    continue
                if infence:
                    w = " ".join(line.split()).lower()
                    if w:
                        spans.add(w)
                    continue
                m = HEADING.match(line)
                if m:
                    heads.append(m.group(1))
                for t in re.findall(r"`([^`\n]+)`", line):
                    spans.add(" ".join(t.split()).lower())
                for t in re.findall(r"\*\*([^*\n]+)\*\*", line):  # **SENTINEL MASTERS** style lists
                    spans.add(" ".join(t.replace("`", "").split()).lower())
            out[rel] = (heads, spans)
    return out


def mentioned(names, spans):
    """True when a code span is the name, or starts with it followed by a space (`maxmemory 2mb`)."""
    for n in names:
        for sp in spans:
            if sp == n or sp.startswith(n + " "):
                return True
    return False


def has_heading(path, want):
    text = safeio.read_text(path)
    infence = False
    for line in text.splitlines():
        if FENCE.match(line):
            infence = not infence
            continue
        m = None if infence else HEADING.match(line)
        if m and m.group(1).lower().startswith(want.lower()):
            return True
    return False


def run(items, docs, out, page_globs, ignore_globs, mention_globs, exclude_globs, adjust=None):
    docs, out = Path(docs), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pages = page_index(docs, mention_globs, exclude_globs) if mention_globs else {}
    ids_by_kind = defaultdict(set)
    rows = []
    for it in items:
        kind, iid = it["kind"], it["id"]
        ids_by_kind[kind].add(iid)
        names = {iid.lower(), " ".join((it.get("name") or "").split()).lower()} - {""}
        names |= {a.lower() for a in (it.get("aliases") or "").split(";") if a}
        own = it.get("expected_page", "")
        hits = [p for p, (_, spans) in pages.items() if p != own and mentioned(names, spans)]
        exp, req = it.get("expected_page", ""), it.get("require_heading", "")
        detail = ""
        if it.get("skip_reason"):
            status, detail = "skipped", it["skip_reason"]
        elif exp:
            p = docs / exp
            if not safeio.readable(p, docs):   # missing, or a name like ../../x escaping docs/
                if hits:
                    status, detail = "no_page_mentioned", f"no {exp}; covered only in other pages"
                else:
                    status, detail = "undocumented", f"no {exp}"
            elif req and not has_heading(p, req):
                status, detail = "missing_heading", f"no '## {req}' heading"
            else:
                status = "documented"
        else:
            status = "mentioned" if hits else "not_mentioned"
        row = dict(it)
        dep_pages = []
        if it.get("deprecated_since") and hits:
            repl = {" ".join(x.split()).lower() for x in re.findall(r"`([^`]+)`", it.get("replaced_by") or "")}
            dep_pages = [p for p in hits if not (repl and mentioned(repl, pages[p][1]))]
        row.update(status=status, detail=detail, mentions=len(hits), pages=";".join(hits[:5]),
                   deprecated_in_use=";".join(dep_pages))
        rows.append(row)

    orphans = []
    for spec in page_globs:
        kind, _, g = spec.partition("=")
        for f in safeio.files(docs, g):
            rel = f.relative_to(docs).as_posix()
            if f.stem in ids_by_kind[kind] or f.stem in ("index", "_index"):
                continue
            reason = "source_not_scanned" if any(fnmatch.fnmatch(rel, x) for x in ignore_globs) else "no_source"
            orphans.append({"kind": kind, "page": rel, "reason": reason})

    if adjust:
        rows = [adjust(r) for r in rows]

    lead = ["kind", "id", "name", "status", "detail", "mentions", "pages"]
    cols = list(lead)
    for r in rows:  # union: extractors may add their own columns (e.g. in_conf)
        cols += [c for c in r if c not in cols]
    with open(out / "coverage.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(out / "orphans.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=["kind", "page", "reason"])
        w.writeheader()
        w.writerows(orphans)

    counts = Counter((r["kind"], r["status"]) for r in rows)
    md = [f"# Coverage: {docs}", "", "| kind | status | count |", "|---|---|---|"]
    md += [f"| {k} | {s} | {n} |" for (k, s), n in sorted(counts.items())]
    oc = Counter((o["kind"], o["reason"]) for o in orphans)
    md += [f"| {k} | orphan page: {r} | {n} |" for (k, r), n in sorted(oc.items())]
    cap = 50
    for status in ("undocumented", "missing_heading", "not_mentioned"):
        gap = [r for r in rows if r["status"] == status]
        if gap:
            md += ["", f"## {status} ({len(gap)})", ""] + [f"- {r['kind']} `{r['name']}` {r['detail']}".rstrip() for r in gap[:cap]]
            if len(gap) > cap:
                md.append(f"- … {len(gap) - cap} more in coverage.csv")
    dep = [r for r in rows if r["deprecated_in_use"]]
    if dep:
        md += ["", f"## deprecated but still used in docs ({len(dep)})", ""]
        md += [f"- `{r['name']}` deprecated since {r['deprecated_since']}, replaced by {r.get('replaced_by') or '?'}: {r['deprecated_in_use']}" for r in dep]
    nmp = [r for r in rows if r["status"] == "no_page_mentioned"]
    if nmp:
        md += ["", f"## no page of their own, covered elsewhere ({len(nmp)})", ""] + [f"- `{r['name']}`: {r['pages']}" for r in nmp]
    nos = [o for o in orphans if o["reason"] == "no_source"]
    if nos:
        md += ["", f"## pages with no source ({len(nos)})", ""] + [f"- {o['page']}" for o in nos]
    (out / "coverage_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return rows, orphans


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items", nargs="+")
    ap.add_argument("--docs", required=True)
    ap.add_argument("--out", default="docs-coverage")
    ap.add_argument("--page-glob", action="append", default=[], help="KIND=GLOB, e.g. command=commands/*.md")
    ap.add_argument("--ignore-glob", action="append", default=[], help="orphan pages whose source wasn't extracted")
    ap.add_argument("--mention-glob", action="append", default=[], help="pages searched for mentions, e.g. topics/*.md")
    ap.add_argument("--exclude-glob", action="append", default=[], help="pages never searched, e.g. generated references")
    a = ap.parse_args()
    rows, orphans = run(read_items(a.items), a.docs, a.out, a.page_glob, a.ignore_glob, a.mention_glob, a.exclude_glob)
    c = Counter(r["status"] for r in rows)
    sys.stderr.write(f"{len(rows)} items: {dict(c)}; orphan pages: {len(orphans)}\nwrote {a.out}/\n")
