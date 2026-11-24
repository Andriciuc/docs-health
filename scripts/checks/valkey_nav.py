#!/usr/bin/env python3
"""Check valkey-doc's menu (nav.yml + modules-nav/*.yml) against the command JSON.

Usage:
  python valkey_nav.py DOC_REPO COMMAND_ITEMS.csv [--out DIR]

COMMAND_ITEMS.csv is items.csv from profile_coverage.py with the valkey profile
(this check runs automatically when a profile lists it under checks). nav.yml rules
(from its header): a "commands" entry is a lowercase group ("list"), an
uppercase container ("ACL", all its subcommands) or an uppercase command
name ("BGSAVE"). The most specific entry wins: name > container > group.
Every documented command should be covered exactly once at its most specific
level; topics should be listed exactly once.

Writes nav_coverage.csv (one row per command: level, entries, status) and
nav_summary.md (including command groups missing from groups.json,
compared with "-" and "_" treated as equal, as the website template does). Statuses: covered, uncovered, ambiguous (>1 entry at the
winning level), skipped (SYSCMD or no doc page). Also lists nav entries that
match no command, and topics listed zero or several times.
"""
import argparse, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import safeio

import yaml


def nav_entries(repo):
    """-> list of (ref, where) and topic list counter"""
    refs, topics = [], Counter()

    def walk(secs, src):
        for s in secs or []:
            where = f"{src}:{s.get('id') or s.get('section')}"
            for c in s.get("commands") or []:
                refs.append((str(c), where + (f"/{s['landing']}" if s.get("landing") else "")))
            if s.get("landing"):
                topics[s["landing"]] += 0  # landing pages are listed, not counted as menu items
            for t in s.get("topics") or []:
                name = t if isinstance(t, str) else t["topic"]
                topics[name] += 1
                if isinstance(t, dict):
                    for c in t.get("commands") or []:
                        refs.append((str(c), f"{where}/{name}"))
    if safeio.readable(repo / "nav.yml", repo):
        walk(yaml.safe_load(safeio.read_text(repo / "nav.yml")), "nav.yml")
    for f in safeio.files(repo, "modules-nav/*.yml"):
        walk(yaml.safe_load(safeio.read_text(f)), f"modules-nav/{f.name}")
    return refs, topics


def norm(s):
    return s.upper().replace("-", " ").replace("_", " ").strip()


def main(repo, items_csv, out):
    repo, out = Path(repo), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cmds = [r for r in safeio.read_csv(items_csv) if r["kind"] == "command"]
    refs, topics = nav_entries(repo)
    by_level = {"name": defaultdict(list), "container": defaultdict(list), "group": defaultdict(list)}
    for ref, where in refs:
        if ref.islower():
            by_level["group"][ref].append(where)
        else:
            by_level["name"][norm(ref)].append(where)
            by_level["container"][norm(ref)].append(where)
    used = set()
    rows = []
    for c in cmds:
        has_page = (repo / c["expected_page"]).exists()
        name, cont = norm(c["name"]), norm(c["container"])
        own_container = cont or name  # a container command (ACL) is covered by its container ref too
        found = None
        for level, key in (("name", name), ("container", own_container if cont else ""), ("group", c["group"])):
            if key and by_level[level].get(key):
                found = (level, key, by_level[level][key])
                break
        if not found and not cont and by_level["container"].get(name):
            found = ("container", name, by_level["container"][name])
        if c["skip_reason"] or not has_page:
            status = "skipped"
            detail = c["skip_reason"] or "no doc page"
        elif not found:
            status, detail = "uncovered", f"group '{c['group']}' not in any menu"
        elif len(found[2]) > 1:
            status, detail = "ambiguous", f"{len(found[2])} entries at level {found[0]}"
        else:
            status, detail = "covered", ""
        if found:
            used.add((found[0], found[1]))
        rows.append({"id": c["id"], "name": c["name"], "group": c["group"], "status": status, "detail": detail,
                     "level": found[0] if found else "", "entries": ";".join(found[2]) if found else ""})
    unmatched = []
    for ref, where in refs:
        level = "group" if ref.islower() else None
        hit = (("group", ref) in used) if level else (("name", norm(ref)) in used or ("container", norm(ref)) in used)
        if not hit:
            unmatched.append((ref, where))
    topic_files = {p.stem for p in safeio.files(repo, "topics/*.md")} - {"index"}
    listed = {t for t, n in topics.items() if n > 0}
    landings = {t for t, n in topics.items() if n == 0}
    not_listed = sorted(topic_files - listed - landings)
    multi = sorted(t for t, n in topics.items() if n > 1)
    missing = sorted(t for t in topics if t not in topic_files)

    with open(out / "nav_coverage.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    cnt = Counter(r["status"] for r in rows)
    md = ["# Menu coverage (nav.yml + modules-nav)", "", "| status | commands |", "|---|---|"]
    md += [f"| {s} | {n} |" for s, n in sorted(cnt.items())]
    for s in ("uncovered", "ambiguous"):
        lst = [r for r in rows if r["status"] == s]
        if lst:
            md += ["", f"## {s} ({len(lst)})", ""] + [f"- `{r['name']}` ({r['group']}): {r['detail']} {r['entries']}".rstrip() for r in lst]
    if unmatched:
        md += ["", f"## menu entries matching no command or unused ({len(unmatched)})", ""] + [f"- `{r}` in {w}" for r, w in unmatched]
    md += ["", "## topics", "", f"- not listed in any menu: {not_listed or 'none'}",
           f"- listed more than once: {multi or 'none'}", f"- listed but no file: {missing or 'none'}"]
    gj = repo / "groups.json"
    if safeio.readable(gj, repo):
        import json
        known = {k.replace("-", "_") for k in json.loads(safeio.read_text(gj))}
        code_groups = sorted({c["group"] for c in cmds if c["group"]})
        unknown = [g for g in code_groups if g.replace("-", "_") not in known]
        md += ["", "## groups.json (command group labels on the website)", "",
               f"- groups in command JSON missing from groups.json: {unknown or 'none'}"]
    (out / "nav_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sys.stderr.write(f"{dict(cnt)}; unmatched menu entries: {len(unmatched)}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("items")
    ap.add_argument("--out", default="docs-coverage")
    a = ap.parse_args()
    main(a.repo, a.items, a.out)
