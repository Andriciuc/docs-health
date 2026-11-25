#!/usr/bin/env python3
"""Build a per-page dataset of a Markdown doc set (MkDocs-aware).

Usage:
  python inventory.py REPO [--config mkdocs.yml ...] [--docs-dir DIR] [--out DIR]
                           [--min-dup-words 25] [--type-rule 'GLOB=TYPE' ...]

Writes to --out (default ./docs-inventory):
  pages.csv       one row per .md page: nav placement, size, structure, freshness, topic-type guess
  nav.csv         one row per nav entry per config (title, path, depth, section, exists)
  links.csv       every internal link/image/snippet with resolution status
  duplicates.csv  paragraphs repeated verbatim across pages (reuse candidates)
  summary.json    counts + issue lists
  summary.md      human-readable digest of summary.json

Stdlib + PyYAML only. Read-only on the repo.
"""
import argparse, fnmatch, hashlib, json, os, re, subprocess, sys, time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio

try:
    import yaml
except ImportError:  # degrade: no config/front matter parsing
    yaml = None

# ---------- YAML helpers ----------
if yaml:
    class _Loader(yaml.SafeLoader):
        pass
    def _any_tag(loader, suffix, node):
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        return loader.construct_mapping(node)
    _Loader.add_multi_constructor("", _any_tag)  # !ENV, !!python/name:..., etc.

def load_yaml(path):
    if not yaml:
        return {}
    try:
        if Path(path).stat().st_size > safeio.MAX_BYTES:
            raise ValueError(f"larger than {safeio.MAX_BYTES} bytes")
        with open(path, encoding="utf-8") as f:
            return yaml.load(f, Loader=_Loader) or {}  # nosec B506 - _Loader subclasses SafeLoader
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"warn: cannot parse {path}: {e}", file=sys.stderr)
        return {}

def load_config(path, root=None, depth=0):
    """Load an MkDocs config, resolving INHERIT (child keys override; nav replaced).
    INHERIT must stay inside root and is followed at most 10 levels (stops cycles)."""
    root = root or Path(path).parent
    cfg = load_yaml(path)
    if not isinstance(cfg, dict):
        return {}
    parent = cfg.get("INHERIT")
    if parent:
        target = safeio.contained(Path(path).parent, parent)
        if target is None or not safeio.inside(target, root):
            safeio.warn(f"ignoring INHERIT {parent!r} in {path}: outside the repo")
            return cfg
        if depth >= 10:
            safeio.warn(f"ignoring INHERIT in {path}: more than 10 levels (cycle?)")
            return cfg
        base = load_config(target.resolve(), root, depth + 1)
        merged = dict(base)
        for k, v in cfg.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = {**merged[k], **v}
            else:
                merged[k] = v
        return merged
    return cfg

def _conf(section, name):
    """plugins / markdown_extensions may be a list (of str|dict) or a mapping."""
    if isinstance(section, dict):
        return (section.get(name) or {}) if name in section else None
    for p in section or []:
        if isinstance(p, dict) and name in p:
            return p[name] or {}
        if p == name:
            return {}
    return None

def plugin_conf(cfg, name):
    return _conf(cfg.get("plugins"), name)

def md_ext_conf(cfg, name):
    return _conf(cfg.get("markdown_extensions"), name)

# ---------- nav ----------
def walk_nav(nav, section=(), depth=1, out=None):
    out = [] if out is None else out
    for item in nav or []:
        if isinstance(item, str):
            out.append({"title": "", "path": item, "depth": depth, "section": " > ".join(section)})
        elif isinstance(item, dict):
            for title, val in item.items():
                if isinstance(val, list):
                    out.append({"title": str(title), "path": "", "depth": depth,
                                "section": " > ".join(section), "is_section": True})
                    walk_nav(val, section + (str(title),), depth + 1, out)
                else:
                    out.append({"title": str(title), "path": str(val or ""), "depth": depth,
                                "section": " > ".join(section)})
    return out

# ---------- markdown parsing ----------
FENCE = re.compile(r"^\s*(```|~~~)")
H = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LINK = re.compile(r"(!?)\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REFDEF = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)")
SNIP = re.compile(r"""--8<--\s+["']([^"']+)["']""")
INCL = re.compile(r"""\{%\s*include\s+["']([^"']+)["']""")
VAR = re.compile(r"\{\{\s*([A-Za-z_][\w\.]*)[^}]*\}\}")
ADMON = re.compile(r"^\s*(!!!|\?\?\?\+?)\s+(\w+)")
OL = re.compile(r"^\s*\d+\.\s+\S")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
TASK_VERBS = ("install", "configure", "enable", "disable", "create", "set up", "setup",
              "upgrade", "run", "connect", "deploy", "add", "remove", "uninstall", "migrate",
              "back up", "restore", "rotate", "verify", "start", "stop", "update", "change",
              "use ", "build", "generate", "monitor", "troubleshoot", "check")

def split_front_matter(text):
    if text.startswith("---"):
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
        if m:
            fm = {}
            if yaml:
                try:
                    fm = yaml.load(m.group(1), Loader=_Loader) or {}  # nosec B506 - SafeLoader subclass
                except (ValueError, yaml.YAMLError):
                    fm = {"_unparseable": True}
            return fm if isinstance(fm, dict) else {}, text[m.end():]
    return {}, text

def parse_page(text):
    fm, body = split_front_matter(text)
    lines = body.splitlines()
    in_code = False
    prose, headings, code_blocks = [], [], 0
    admons, ol_items, table_rows = 0, 0, 0
    for ln in lines:
        if FENCE.match(ln):
            in_code = not in_code
            if in_code:
                code_blocks += 1
            continue
        if in_code:
            continue
        prose.append(ln)
        m = H.match(ln)
        if m:
            headings.append((len(m.group(1)), m.group(2)))
        if ADMON.match(ln):
            admons += 1
        if OL.match(ln):
            ol_items += 1
        if TABLE_ROW.match(ln):
            table_rows += 1
    prose_text = "\n".join(prose)
    words = len(re.findall(r"[A-Za-z0-9_']+", re.sub(r"\(([^)]*)\)", " ", prose_text)))
    return {
        "fm": fm, "body": body, "prose": prose_text, "headings": headings,
        "code_blocks": code_blocks, "admonitions": admons, "ol_items": ol_items,
        "table_rows": table_rows, "words": words,
    }

def paragraphs(prose):
    for block in re.split(r"\n\s*\n", prose):
        b = block.strip()
        if not b or b.startswith(("#", "|", "--8<--", "!!!", "???")):
            continue
        yield b

def guess_type(rel, p):
    """Heuristic topic type + the signals that drove it. Always a guess; verify."""
    low = rel.lower()
    hs = [h.lower() for _, h in p["headings"]]
    sig = []
    if "release-notes" in low or "release_notes" in low or re.search(r"(^|/)rn[-_]", low):
        return "release-notes", "path"
    links_out = len(LINK.findall(p["prose"]))
    if p["words"] < 150 and links_out >= 4:
        return "landing", f"words={p['words']} links={links_out}"
    task_heads = sum(1 for h in hs if h.startswith(TASK_VERBS))
    if p["ol_items"] >= 3: sig.append(f"ol={p['ol_items']}")
    if task_heads: sig.append(f"verb_headings={task_heads}")
    if p["code_blocks"] >= 2: sig.append(f"code={p['code_blocks']}")
    task_score = (p["ol_items"] >= 3) + (task_heads >= 1) + (p["code_blocks"] >= 2)
    ref_score = (p["table_rows"] >= 8) + any(k in low for k in ("reference", "parameters", "functions", "variables", "commands/", "api")) \
        + (p["table_rows"] >= 3 and p["words"] < 400)
    if p["table_rows"]: sig.append(f"table_rows={p['table_rows']}")
    if ref_score >= 2 or (ref_score == 1 and task_score == 0 and p["table_rows"] >= 8):
        t = "reference"
    elif task_score >= 2:
        t = "task"
    elif task_score == 1 and p["words"] < 600:
        t = "task?"
    else:
        t = "concept"
    if t in ("task", "task?") and ref_score >= 1 and p["words"] > 800:
        t = "mixed"
    return t, " ".join(sig)

# ---------- git ----------
def git_history(repo, subdir, bulk=30, skip_subject=None):
    """Last commit time + commit count per file. Commits touching > bulk files
    (reformat, rename, link sweep) are ignored for age so they don't fake freshness."""
    try:
        shallow = subprocess.run(["git", "-C", str(repo), "rev-parse", "--is-shallow-repository"],
                                 capture_output=True, text=True, check=False, env=safeio.GIT_ENV,
                                 timeout=safeio.GIT_TIMEOUT).stdout.strip() == "true"
        # core.quotepath=off: otherwise git prints non-ASCII paths as "caf\303\251.md" and they never match.
        # Decode as UTF-8 explicitly: text=True alone uses the locale code page (cp1252 on Windows).
        out = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", "log", "--format=__C__%ct %s", "--name-only",
                              "--", str(subdir)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
                             env=safeio.GIT_ENV, timeout=safeio.GIT_TIMEOUT).stdout
    except (OSError, subprocess.SubprocessError):
        return {}, {}, None, 0
    commits, cur = [], None
    for ln in out.splitlines():
        if ln.startswith("__C__"):
            ts_, _, subj = ln[5:].partition(" ")
            cur = (int(ts_), [], subj); commits.append(cur)
        elif ln.strip() and cur:
            cur[1].append(ln.strip())
    last, last_any, count, skipped = {}, {}, defaultdict(int), 0
    for ts, files, subj in commits:  # newest first
        is_bulk = (bulk and len(files) > bulk) or bool(skip_subject and re.search(skip_subject, subj))
        skipped += bool(is_bulk)
        for f in files:
            count[f] += 1
            last_any.setdefault(f, ts)
            if not is_bulk:
                last.setdefault(f, ts)
    for f, ts in last_any.items():  # only ever touched in bulk (e.g. initial import): use that
        last.setdefault(f, ts)
    return last, count, shallow, skipped

# ---------- main ----------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("--config", action="append", help="mkdocs config(s), relative to repo; repeatable. Default: auto-detect mkdocs*.yml")
    ap.add_argument("--docs-dir", help="override docs_dir (relative to repo)")
    ap.add_argument("--out", default="docs-inventory")
    ap.add_argument("--min-dup-words", type=int, default=25)
    ap.add_argument("--bulk-commit-files", type=int, default=30,
                    help="ignore commits touching more than N files when computing page age (0 = off)")
    ap.add_argument("--ignore-commit-subject", metavar="REGEX",
                    help="also ignore commits whose subject matches REGEX for page age, e.g. 'mentions to [0-9]+|bump version'")
    ap.add_argument("--type-rule", action="append", default=[], metavar="GLOB=TYPE",
                    help="force topic type for paths matching GLOB (relative to docs_dir), e.g. 'commands/*.md=reference'; repeatable, first match wins")
    a = ap.parse_args(argv)

    repo = Path(a.repo).resolve()
    cfg_paths = [repo / c for c in a.config] if a.config else (
        safeio.files(repo, "mkdocs*.yml") + safeio.files(repo, "*/mkdocs*.yml"))
    configs = {}
    for cp in cfg_paths:
        c = load_config(cp, repo)
        if c:
            configs[str(cp.relative_to(repo))] = (cp, c)

    # docs_dir: from first config (they normally share it)
    if a.docs_dir:
        docs_dir = repo / a.docs_dir
        cfg_root = repo
    elif configs:
        cp, c = next(iter(configs.values()))
        cfg_root = cp.parent
        docs_dir = cfg_root / str(c.get("docs_dir") or "docs")
        if not safeio.inside(docs_dir, repo):
            sys.exit(f"docs_dir {c.get('docs_dir')!r} in {cp} points outside the repo")
    else:
        cfg_root, docs_dir = repo, repo
    site_url, dir_urls = "", True
    if configs:
        _c = next(iter(configs.values()))[1]
        for _, (_cp, _cc) in configs.items():  # prefer a config that sets site_url
            if _cc.get("site_url"):
                _c = _cc; break
        site_url = str(_c.get("site_url") or "")
        dir_urls = _c.get("use_directory_urls", True) is not False
    if not docs_dir.is_dir():
        sys.exit(f"docs dir not found: {docs_dir}")

    # variables (mkdocs-macros include_yaml + extra)
    known_vars = {"config", "page", "nav", "base_url", "extra", "git", "environment", "macros_info", "now", "fix_url"}
    var_files = []
    for _, (cp, c) in configs.items():
        known_vars |= set((c.get("extra") or {}).keys())
        mac = plugin_conf(c, "macros")
        if mac is not None:
            for entry in mac.get("include_yaml") or []:
                f = next(iter(entry.values()), None) if isinstance(entry, dict) else entry
                vf = safeio.contained(cp.parent, f)
                if vf is not None and safeio.inside(vf, repo):
                    var_files.append(vf)
    if not var_files and (cfg_root / "variables.yml").exists():
        var_files.append(cfg_root / "variables.yml")
    for vf in var_files:
        if safeio.readable(vf, repo):
            known_vars |= set((load_yaml(vf) or {}).keys())
    has_macros = any(plugin_conf(c, "macros") is not None for _, c in configs.values())

    snip_bases = [cfg_root]
    for _, c in configs.values():
        sc = md_ext_conf(c, "pymdownx.snippets")
        if sc and sc.get("base_path"):
            bp = sc["base_path"]
            snip_bases += [cfg_root / b for b in (bp if isinstance(bp, list) else [bp])
                           if safeio.inside(cfg_root / str(b), repo)]

    # nav
    nav_rows, nav_sets = [], {}
    for name, (_cp, c) in configs.items():
        entries = walk_nav(c.get("nav"))
        nav_sets[name] = {}
        for i, e in enumerate(entries):
            path = e["path"]
            external = bool(re.match(r"^[a-z]+://", path))
            exists = "" if (not path or external) else (docs_dir / path).is_file()
            nav_rows.append({"config": name, "order": i, "depth": e["depth"], "section": e["section"],
                             "title": e["title"], "path": path, "is_section": e.get("is_section", False),
                             "external": external, "exists": exists})
            if path and not external:
                nav_sets[name][path] = e

    # pages
    md_files = safeio.rglob(docs_dir, "*.md")
    last, count, shallow, bulk_skipped = git_history(repo, docs_dir.relative_to(repo) if docs_dir != repo else ".", a.bulk_commit_files, a.ignore_commit_subject)
    now = time.time()
    pages, link_rows, par_index = [], [], defaultdict(list)
    snippet_targets = set()
    all_rel = {str(p.relative_to(docs_dir)).replace(os.sep, "/") for p in md_files}

    for p in md_files:
        rel = str(p.relative_to(docs_dir)).replace(os.sep, "/")
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        pp = parse_page(text)
        fm = pp["fm"]
        h1 = next((t for l, t in pp["headings"] if l == 1), "")
        title = str(fm.get("title") or h1 or "")
        ttype, sig = guess_type(rel, pp)
        for rule in a.type_rule:
            g, _, t = rule.partition("=")
            if fnmatch.fnmatch(rel, g):
                ttype, sig = t, f"rule:{g}"
                break

        # links
        refdefs = {m.group(1).lower(): m.group(2) for m in map(REFDEF.match, pp["prose"].splitlines()) if m}
        targets = [("image" if bang else "link", t) for bang, _, t in LINK.findall(pp["prose"])]
        targets += [("link", v) for v in refdefs.values()]
        n_int = n_ext = n_broken = 0
        for kind, t in targets:
            if re.match(r"^(https?:|mailto:|ftp:)", t):
                n_ext += 1
                link_rows.append({"page": rel, "kind": kind, "target": t, "scope": "external", "status": "unchecked"})
                continue
            if t.startswith("#") or "{{" in t:
                continue
            n_int += 1
            path_part = t.split("#")[0].split("?")[0]
            if not path_part:
                continue
            # "/x.md" is relative to docs_dir; joining it as-is would drop docs_dir and resolve to the filesystem root.
            tgt = (docs_dir / path_part.lstrip("/")) if path_part.startswith("/") else (p.parent / path_part)
            tgt = Path(os.path.normpath(tgt))
            ok = tgt.exists() or (tgt.is_dir() and (tgt / "index.md").exists()) \
                or Path(str(tgt).rstrip("/") + ".md").exists() or (Path(str(tgt).rstrip("/")) / "index.md").exists()
            if not ok:
                n_broken += 1
            link_rows.append({"page": rel, "kind": kind, "target": t, "scope": "internal",
                              "status": "ok" if ok else "broken"})
        snips = SNIP.findall(pp["body"]) + INCL.findall(pp["body"])
        for s in snips:
            found = None
            for b in snip_bases + [p.parent, docs_dir]:
                if safeio.inside(b / s, repo) and (b / s).exists():
                    found = (b / s).resolve()
                    break
            if found:
                try:
                    snippet_targets.add(str(found.relative_to(docs_dir.resolve())).replace(os.sep, "/"))
                except ValueError:
                    pass
            link_rows.append({"page": rel, "kind": "snippet", "target": s, "scope": "internal",
                              "status": "ok" if found else "broken"})
            if not found:
                n_broken += 1
        vars_used = sorted(set(VAR.findall(pp["body"])))
        undefined = [v for v in vars_used if v.split(".")[0] not in known_vars] if has_macros else []

        for para in paragraphs(pp["prose"]):
            norm = re.sub(r"\s+", " ", para.lower())
            if len(norm.split()) >= a.min_dup_words:
                par_index[hashlib.sha1(norm.encode(), usedforsecurity=False).hexdigest()[:12]].append((rel, para[:160].replace("\n", " ")))

        git_rel = str(p.relative_to(repo)).replace(os.sep, "/")
        ts = last.get(git_rel)
        stem = rel[:-3]
        if dir_urls:
            stem = stem[:-5] if stem.endswith("index") else stem + "/"
            url_path = stem
        else:
            url_path = stem + ".html"
        row = {
            "path": rel, "url": (site_url.rstrip("/") + "/" + url_path) if site_url else "/" + url_path, "title": title,
            "words": pp["words"], "h2": sum(1 for l, _ in pp["headings"] if l == 2),
            "max_heading": max([l for l, _ in pp["headings"]] or [0]),
            "h1_count": sum(1 for l, _ in pp["headings"] if l == 1),
            "code_blocks": pp["code_blocks"], "admonitions": pp["admonitions"],
            "ol_items": pp["ol_items"], "table_rows": pp["table_rows"],
            "links_internal": n_int, "links_external": n_ext, "links_broken": n_broken,
            "snippets": len(snips), "vars_used": " ".join(vars_used), "vars_undefined": " ".join(undefined),
            "front_matter_keys": " ".join(sorted(fm.keys())) if isinstance(fm, dict) else "",
            "type_guess": ttype, "type_signals": sig,
            "last_commit": time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else "",
            "days_since_commit": int((now - ts) / 86400) if ts else "",
            "commits": count.get(git_rel, 0),
        }
        for name in configs:
            e = nav_sets[name].get(rel)
            row[f"nav:{name}"] = "" if e is None else (e["section"] + " > " + (e["title"] or title)).strip(" >")
            row[f"depth:{name}"] = "" if e is None else e["depth"]
        pages.append(row)

    # inbound links (findability signal)
    inbound = defaultdict(int)
    for lr in link_rows:
        if lr["scope"] == "internal" and lr["kind"] == "link" and lr["status"] == "ok":
            src = docs_dir / lr["page"]
            tgt = os.path.normpath(src.parent / lr["target"].split("#")[0])
            try:
                inbound[str(Path(tgt).relative_to(docs_dir)).replace(os.sep, "/")] += 1
            except ValueError:
                pass
    for r in pages:
        r["links_inbound"] = inbound.get(r["path"], 0)
        r["used_as_snippet"] = r["path"] in snippet_targets

    dups = [(h, v) for h, v in par_index.items() if len({x[0] for x in v}) >= 2]

    # ---------- summary ----------
    in_any_nav = set().union(*[set(s) for s in nav_sets.values()]) if nav_sets else set()
    orphans = sorted(r["path"] for r in pages if nav_sets and r["path"] not in in_any_nav
                     and not r["used_as_snippet"] and not r["path"].startswith(("snippets/", "_", "templates/")))
    per_config = {}
    for name, s in nav_sets.items():
        per_config[name] = {
            "nav_pages": len(s),
            "nav_missing_files": sorted(p for p in s if p not in all_rel),
            "pages_not_in_this_nav": len([r for r in pages if r["path"] not in s]),
            "max_depth": max([e["depth"] for e in s.values()] or [0]),
            "dup_nav_entries": sorted({r["path"] for r in nav_rows if r["config"] == name and r["path"]
                                      and sum(1 for x in nav_rows if x["config"] == name and x["path"] == r["path"]) > 1}),
        }
    nav_drift = {}
    names = list(nav_sets)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            A, B = set(nav_sets[names[i]]), set(nav_sets[names[j]])
            if A != B:
                nav_drift[f"{names[i]} vs {names[j]}"] = {"only_in_first": sorted(A - B), "only_in_second": sorted(B - A)}
    type_mix = defaultdict(int)
    for r in pages: type_mix[r["type_guess"]] += 1
    ages = sorted(r["days_since_commit"] for r in pages if r["days_since_commit"] != "")
    summary = {
        "repo": str(repo), "docs_dir": str(docs_dir.relative_to(repo)) if docs_dir != repo else ".",
        "configs": list(configs), "git_shallow": shallow,
        "pages": len(pages), "words_total": sum(r["words"] for r in pages),
        "type_mix_guess": dict(type_mix),
        "per_config": per_config, "nav_drift": nav_drift,
        "orphans_not_in_any_nav": orphans,
        "broken_internal": [lr for lr in link_rows if lr["status"] == "broken"],
        "undefined_variables": {r["path"]: r["vars_undefined"] for r in pages if r["vars_undefined"]},
        "pages_without_h1_or_title": [r["path"] for r in pages if not r["title"]],
        "pages_multiple_h1": [r["path"] for r in pages if r["h1_count"] > 1],
        "duplicate_paragraph_groups": len(dups),
        "bulk_commits_ignored_for_age": bulk_skipped,
        "age_days": {"median": ages[len(ages)//2] if ages else None,
                     "over_365": sum(1 for x in ages if x > 365), "known": len(ages)},
        "front_matter_usage": {k: sum(1 for r in pages if k in r["front_matter_keys"].split())
                               for k in sorted({k for r in pages for k in r["front_matter_keys"].split()})},
    }

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    def wcsv(name, rows, fields=None):
        fields = fields or (list(rows[0].keys()) if rows else ["empty"])
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = safeio.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    wcsv("pages.csv", pages)
    wcsv("nav.csv", nav_rows, ["config", "order", "depth", "section", "title", "path", "is_section", "external", "exists"])
    wcsv("links.csv", link_rows, ["page", "kind", "target", "scope", "status"])
    wcsv("duplicates.csv", [{"group": h, "page": pg, "excerpt": ex} for h, v in dups for pg, ex in v],
         ["group", "page", "excerpt"])
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    md = [f"# Inventory: {repo.name}", "",
          f"- docs_dir: `{summary['docs_dir']}`; configs: {', '.join(summary['configs']) or 'none (plain Markdown)'}",
          f"- pages: {summary['pages']}; words: {summary['words_total']}",
          f"- type mix (heuristic): {summary['type_mix_guess']}",
          f"- git: median age {summary['age_days']['median']} d, >365 d: {summary['age_days']['over_365']}"
          + f"; {bulk_skipped} bulk commits (>{a.bulk_commit_files} files) ignored"
          + (" (SHALLOW CLONE: ages/commit counts are lower bounds)" if shallow else ""),
          f"- orphans (not in any nav): {len(orphans)}",
          f"- broken internal links/snippets: {len(summary['broken_internal'])}",
          f"- pages with undefined variables: {len(summary['undefined_variables'])}",
          f"- duplicate paragraph groups (>= {a.min_dup_words} words): {len(dups)}", ""]
    for name, pc in per_config.items():
        md.append(f"## {name}: {pc['nav_pages']} nav pages, max depth {pc['max_depth']}, "
                  f"{len(pc['nav_missing_files'])} missing files, {len(pc['dup_nav_entries'])} duplicate entries")
        for m in pc["nav_missing_files"]: md.append(f"- missing: `{m}`")
    for k, d in nav_drift.items():
        md.append(f"## Nav drift: {k}")
        md.append(f"- only in first: {len(d['only_in_first'])}; only in second: {len(d['only_in_second'])}")
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nwrote {out}/: pages.csv nav.csv links.csv duplicates.csv summary.json summary.md")

if __name__ == "__main__":
    main()
