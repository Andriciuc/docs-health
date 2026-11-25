#!/usr/bin/env python3
"""Compile a scan's Markdown reports and CSV data into one self-contained HTML page.

Usage:
  python html_report.py OUT_DIR [OUT_DIR ...] [--out report.html] [--title TEXT]
                        [--max-rows N]

Collects from each folder (non-recursive):
  *.md    rendered as report sections, the main report first: files named
          *report*.md, then optimizations.md, then the rest alphabetically
  *.csv   rendered as tables (click a header to sort, type to filter)
  *.tsv   same as CSV, tab-separated

Works for inventory (inv/), compare (cmp/) and coverage (cov/) output, or several
folders at once. The page has no external assets and uses ES5 script only, so it
opens offline in any browser, including old ones, and can be attached to an
issue, emailed or published as is.

--max-rows caps very large tables (default 5000 rows per table); the cap is
noted under the table and the full CSV stays next to the report.

Stdlib only. The Markdown renderer handles what these reports use: headings,
paragraphs, lists, tables, fenced code, inline code, bold, italics and links.
"""
import argparse, csv, html, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio


# ---------- Markdown (subset) ----------

SAFE_URL = re.compile(r"^(https?://|mailto:|#|/|\./|\.\./|[A-Za-z0-9_.-]+(/|$|#|\.))", re.I)


def link(m):
    """Render [text](url) only for http(s), mailto, anchors and relative paths; anything else
    (javascript:, data:, ...) stays as plain text. The URL is attribute-escaped."""
    url = html.unescape(m.group(2))
    if not SAFE_URL.match(url) or (":" in url.split("/")[0] and not url.lower().startswith(("http://", "https://", "mailto:"))):
        return m.group(0)
    return '<a href="%s" rel="noopener noreferrer">%s</a>' % (html.escape(url, quote=True), m.group(1))


def inline(text):
    # Code spans first, behind placeholders, so bold/italic/links can wrap them.
    codes = []

    def keep(m):
        codes.append("<code>%s</code>" % html.escape(m.group(1)))
        return "\x00%d\x00" % (len(codes) - 1)
    s = re.sub(r"`([^`]*)`", keep, text)
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", s)
    return re.sub("\x00(\\d+)\x00", lambda m: codes[int(m.group(1))], s)


def md_to_html(text, id_prefix):
    lines = text.splitlines()
    out, i, para = [], 0, []

    def flush():
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
            del para[:]

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            flush()
            fence, buf = line.strip()[:3], []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                buf.append(lines[i])
                i += 1
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(buf)))
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            flush()
            level = min(len(m.group(1)) + 1, 6)  # the page owns <h1>
            slug = id_prefix + "-" + re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            out.append('<h%d id="%s">%s</h%d>' % (level, slug, inline(m.group(2)), level))
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            flush()
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            t = ["<table><thead><tr>"] + ["<th>%s</th>" % inline(c) for c in head] + ["</tr></thead><tbody>"]
            for r in body:
                t.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r))
            t.append("</tbody></table>")
            out.append("".join(t))
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            flush()
            tag = "ol" if m.group(2)[0].isdigit() else "ul"
            items = []
            while i < len(lines):
                m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if m:
                    items.append(m.group(3))
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()
                else:
                    break
                i += 1
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x) for x in items), tag))
            continue
        if not line.strip():
            flush()
        elif line.startswith(">"):
            flush()
            out.append("<blockquote>%s</blockquote>" % inline(line.lstrip("> ")))
        else:
            para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


# ---------- CSV ----------

def csv_table(path, tid, max_rows):
    delim = "\t" if path.suffix == ".tsv" else ","
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=delim))
    if not rows:
        return "<p class='n'>empty</p>", 0
    head, body = rows[0], rows[1:]
    shown = body[:max_rows]
    t = ['<div class="wrap"><table class="data" id="%s"><thead><tr>' % tid]
    t += ['<th onclick="sortT(this)">%s</th>' % html.escape(c) for c in head]
    t.append("</tr></thead><tbody>")
    for r in shown:
        t.append("<tr>%s</tr>" % "".join("<td>%s</td>" % html.escape(safeio.uncell(c)) for c in r))
    t.append("</tbody></table></div>")
    note = "%d rows" % len(body)
    if len(shown) < len(body):
        note += " (first %d shown; full data in %s)" % (len(shown), path.name)
    t.append('<p class="n">%s</p>' % note)
    return "".join(t), len(body)


# ---------- Page ----------

CSS = """body{font-family:"Segoe UI",Arial,sans-serif;margin:0;color:#1d2330;background:#fff;font-size:14px;line-height:1.5}
#side{position:fixed;top:0;left:0;bottom:0;width:240px;overflow:auto;background:#f3f5f8;border-right:1px solid #d9dee6;padding:16px;box-sizing:border-box}
#side h1{font-size:15px;margin:0 0 4px}#side .meta{color:#5a6478;font-size:12px;margin-bottom:10px}
#side ul{list-style:none;padding:0;margin:0 0 12px}#side li{margin:3px 0}#side a{color:#2b4a8a;text-decoration:none;font-size:13px}
#side h2{font-size:12px;text-transform:uppercase;color:#5a6478;margin:12px 0 4px}
#main{margin-left:240px;padding:20px 32px;max-width:1200px;box-sizing:border-box}
section{border-bottom:1px solid #e3e7ee;padding-bottom:16px;margin-bottom:20px}
h1,h2,h3,h4{color:#13203a}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:12.5px}
th,td{border:1px solid #d9dee6;padding:4px 6px;text-align:left;vertical-align:top;word-wrap:break-word}
th{background:#e9edf3}table.data th{cursor:pointer}tr:nth-child(even) td{background:#fafbfc}
code{background:#eef1f5;padding:0 3px;font-family:Consolas,monospace;font-size:12px}
pre{background:#eef1f5;padding:8px;overflow:auto}blockquote{border-left:3px solid #c9d1de;margin:8px 0;padding:2px 10px;color:#3c4659}
.wrap{overflow-x:auto;max-width:100%}.wrap td{max-width:420px}
.n,.src{color:#5a6478;font-size:12px}input{border:1px solid #b9c1cf;padding:2px 6px;font-size:12px}
@media print{#side{display:none}#main{margin-left:0}}"""

JS = """function txt(c){return c.innerText!==undefined?c.innerText:c.textContent;}
function sortT(th){var t=th.parentNode.parentNode.parentNode,tb=t.tBodies[0],i=0,c=th;while(c=c.previousSibling)if(c.nodeType===1)i++;
var asc=th.getAttribute("data-asc")!=="1";th.setAttribute("data-asc",asc?"1":"0");var rows=[],k;for(k=0;k<tb.rows.length;k++)rows.push(tb.rows[k]);
rows.sort(function(a,b){var x=txt(a.cells[i]),y=txt(b.cells[i]),r;
if(/^-?[0-9.]+$/.test(x)&&/^-?[0-9.]+$/.test(y))r=parseFloat(x)-parseFloat(y);else r=x<y?-1:(x>y?1:0);return asc?r:-r;});
for(k=0;k<rows.length;k++)tb.appendChild(rows[k]);}
function filt(inp,id){var q=inp.value.toLowerCase(),tb=document.getElementById(id).tBodies[0],k;
for(k=0;k<tb.rows.length;k++){tb.rows[k].style.display=txt(tb.rows[k]).toLowerCase().indexOf(q)>-1?"":"none";}}"""


def md_order(p):
    n = p.name.lower()
    return (0 if "report" in n else 1 if n.startswith("optimization") else 2, n)


def build(dirs, title, max_rows):
    reports, tables, sources = [], [], []
    multi = len(dirs) > 1
    for d_arg in dirs:
        d = Path(d_arg)
        sources.append(str(d))
        label = (d.name + "/") if multi else ""
        for p in sorted(d.glob("*.md"), key=md_order):
            sid = "md-%d" % len(reports)
            body = md_to_html(p.read_text(encoding="utf-8-sig", errors="replace"), sid)
            m = re.search(r"^#\s+(.+)$", p.read_text(encoding="utf-8-sig", errors="replace"), re.M)
            reports.append((sid, label + (m.group(1) if m else p.stem), p, body))
        for p in sorted(list(d.glob("*.csv")) + list(d.glob("*.tsv"))):
            tid = "t-%d" % len(tables)
            table, n = csv_table(p, tid, max_rows)
            tables.append((tid, label + p.name, n, table))
    nav = ["<h2>Reports</h2><ul>"] + ['<li><a href="#%s">%s</a></li>' % (s, html.escape(t)) for s, t, _, _ in reports] + ["</ul>"]
    nav += ["<h2>Data</h2><ul>"] + ['<li><a href="#%s-s">%s (%d)</a></li>' % (t, html.escape(n), c) for t, n, c, _ in tables] + ["</ul>"]
    main = []
    for sid, _t, p, body in reports:
        main.append('<section id="%s"><p class="src">Source: <code>%s</code></p>%s</section>' % (sid, html.escape(p.name), body))
    for tid, name, _n, table in tables:
        main.append('<section id="%s-s"><h2>Data: %s</h2><p class="src">Click a header to sort. '
                    '<input type="text" placeholder="Filter rows" oninput="filt(this,\'%s\')" onkeyup="filt(this,\'%s\')"></p>%s</section>'
                    % (tid, html.escape(name), tid, tid, table))
    meta = "Generated %s from %s" % (date.today().isoformat(), ", ".join(html.escape(s) for s in sources))
    return ('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta http-equiv="X-UA-Compatible" content="IE=edge"><meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>%s</title><style>%s</style></head><body>"
            '<div id="side"><h1>%s</h1><div class="meta">%s</div>%s</div>'
            '<div id="main">%s</div><script>%s</script></body></html>\n'
            % (html.escape(title), CSS, html.escape(title), meta, "".join(nav), "\n".join(main), JS))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", help="default: <first dir>/report.html")
    ap.add_argument("--title", default="Docs health report")
    ap.add_argument("--max-rows", type=int, default=5000)
    a = ap.parse_args(argv)
    for d in a.dirs:
        if not Path(d).is_dir():
            sys.exit("not a directory: %s" % d)
    out = Path(a.out) if a.out else Path(a.dirs[0]) / "report.html"
    out.write_text(build(a.dirs, a.title, a.max_rows), encoding="utf-8")
    sys.stderr.write("wrote %s\n" % out)


if __name__ == "__main__":
    main()
