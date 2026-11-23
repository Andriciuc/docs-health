#!/usr/bin/env python3
"""Join pages.csv (from inventory.py) with an analytics export keyed by URL or path.

Usage:
  python join_analytics.py pages.csv analytics.csv [--key COLUMN] [--out joined.csv]

analytics.csv: any CSV export (GA4 "Pages and screens", Search Console "Pages",
Plausible...). --key names its URL/path column; default: first header containing
"page", "url" or "path". GA4 '#' comment lines are skipped.

Matching: both sides are reduced to path segments (scheme/host, query, fragment,
.html and trailing slashes dropped; "dir/" and "dir/index.html" -> "dir/index").
An analytics row matches the page whose segments are the longest suffix of the
row's segments, so site prefixes and version folders (/postgresql/19/apt.html)
match apt.md. The segment just before the match is recorded as `version` when it
looks like one (digits/dots, "latest", "main", "dev").

Outputs (next to --out):
  joined.csv             every page + metrics across versions (blank = no traffic). Counts are
                         summed; ratio/average columns (per, average, rate, CTR, position, time)
                         are means weighted by the first count column (e.g. Views, Clicks).
  joined_by_version.csv  page, version, metrics (long format)
  unmatched.csv          analytics rows matching no page -> renamed/deleted URLs = redirect candidates
"""
import argparse, csv, re, sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

VERSION = re.compile(r"^(\d+(\.\d+)*|latest|main|dev|stable)$")

def segs(u):
    u = u.strip()
    if re.match(r"^[a-z]+://", u):
        u = urlparse(u).path
    u = u.split("?")[0].split("#")[0]
    if u.endswith("/") or u == "":
        u += "index"
    u = re.sub(r"\.html?$", "", u)
    return [s for s in u.split("/") if s]

def num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("pages"); ap.add_argument("analytics")
ap.add_argument("--key"); ap.add_argument("--out", default="joined.csv")
a = ap.parse_args()

pages = list(csv.DictReader(open(a.pages, encoding="utf-8")))
with open(a.analytics, encoding="utf-8-sig") as f:
    lines = [l for l in f if not l.startswith("#") and l.strip()]
rows = list(csv.DictReader(lines))
if not rows:
    sys.exit("analytics file has no rows")
key = a.key or next((h for h in rows[0] if re.search(r"page|url|path", h, re.I)), None)
if not key:
    sys.exit(f"no URL column found; pass --key. Columns: {list(rows[0])}")
metrics = [h for h in rows[0] if h != key and any(r[h] for r in rows)
           and all(num(r[h]) is not None for r in rows[:200] if r[h])]

RATIO = re.compile(r"per |average|avg|rate|ratio|ctr|position|%|duration|time", re.I)
ratio = [m for m in metrics if RATIO.search(m)]
additive = [m for m in metrics if m not in ratio]
weight_col = additive[0] if additive else None  # e.g. Views / Clicks: weights for ratio metrics

# page key = docs-relative path without .md ("solutions/ha-patroni", "index")
page_keys = {tuple(p["path"][:-3].split("/")): p for p in pages}
maxlen = max(len(k) for k in page_keys)

agg = defaultdict(lambda: defaultdict(float))
by_ver = defaultdict(lambda: defaultdict(float))
unmatched = []
for r in rows:
    s = segs(r[key])
    hit = None
    for n in range(min(len(s), maxlen), 0, -1):
        if tuple(s[-n:]) in page_keys:
            hit, rest = page_keys[tuple(s[-n:])], s[:-n]
            break
    if not hit:
        unmatched.append(r); continue
    ver = rest[-1] if rest and VERSION.match(rest[-1]) else ""
    wt = (num(r[weight_col]) or 0) if weight_col else 1
    for d in (agg[hit["path"]], by_ver[(hit["path"], ver)]):
        for m in additive:
            d[m] += num(r[m]) or 0
        for m in ratio:
            d[m] += (num(r[m]) or 0) * wt
        d["__w"] += wt

def final(d):
    return {m: round(d[m] if m in additive else (d[m] / d["__w"] if d["__w"] else 0), 2) for m in metrics}

out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(pages[0]) + metrics); w.writeheader()
    for p in pages:
        w.writerow({**p, **(final(agg[p["path"]]) if p["path"] in agg else {m: "" for m in metrics})})
with open(out.with_name("joined_by_version.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["path", "version"] + metrics)
    for (pth, ver), d in sorted(by_ver.items()):
        f_ = final(d); w.writerow([pth, ver] + [f_[m] for m in metrics])
with open(out.with_name("unmatched.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(unmatched)
print(f"key={key!r} summed={additive} weighted-mean (by {weight_col})={ratio}")
users = [m for m in additive if re.search(r"user|visitor|session", m, re.I)]
if users:
    print(f"warning: {users} summed across URLs/versions; this overcounts unique users")
print(f"pages with traffic: {len(agg)}/{len(pages)}; analytics rows: {len(rows)}, unmatched: {len(unmatched)}")
print(f"versions seen: {sorted({v for _, v in by_ver}) }")
print(f"wrote {out}, {out.with_name('joined_by_version.csv')}, {out.with_name('unmatched.csv')}")
