#!/usr/bin/env python3
"""Docs-vs-code coverage for any project, driven by a YAML profile.

Usage:
  python profile_coverage.py PROFILE --code CODE_DIR --docs DOCS_DIR [--out DIR]
  python profile_coverage.py PROFILE --print-sparse        # code paths the profile reads

PROFILE is a built-in name (a file in profiles/, e.g. "valkey") or a path to a
.yml/.yaml file. The profile says where the documentable items are in the code
(JSON/YAML fields or a regex), what each item needs in the docs (its own page, a
heading on that page, or a mention), and when to skip one. This script turns the
code into items, then runs coverage.py's matcher on the docs.

Writes to --out (default ./docs-coverage):
  items.csv             every extracted item (common items format)
  coverage.csv, orphans.csv, coverage_summary.md   from coverage.py
  plus the output of any checks the profile lists (e.g. valkey_nav)

Profile reference: README.md, "Write your own profile". Example: profiles/valkey.yml.

Safety: globs must be relative and stay inside the code/docs folders; templates
only substitute {field} values (no expressions); checks come from a fixed list.
Stdlib + PyYAML.
"""
import argparse, csv, fnmatch, json, re, sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "checks")]
import coverage  # noqa: E402

FIELDS = ["kind", "id", "name", "aliases", "expected_page", "require_heading", "skip_reason",
          "source_path", "group", "container", "since", "deprecated_since", "replaced_by"]
SOURCES = ("json", "yaml", "regex")
REGEX_FLAGS = {"MULTILINE": re.M, "DOTALL": re.S, "IGNORECASE": re.I}
TEMPLATE = re.compile(r"\{(\w+)\}")


class ProfileError(ValueError):
    pass


# ---------- profile loading ----------

def resolve_profile(spec):
    p = Path(spec)
    if p.suffix in (".yml", ".yaml") or "/" in spec or "\\" in spec:
        if not p.is_file():
            raise ProfileError(f"profile not found: {spec}")
        return p
    built_in = HERE.parent / "profiles" / f"{spec}.yml"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", spec) or not built_in.is_file():
        names = sorted(x.stem for x in (HERE.parent / "profiles").glob("*.yml"))
        raise ProfileError(f"unknown built-in profile {spec!r} (available: {', '.join(names) or 'none'})")
    return built_in


def safe_glob(g):
    if not isinstance(g, str) or not g or g.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", g) \
            or ".." in Path(g).parts:
        raise ProfileError(f"glob must be relative and stay inside the folder: {g!r}")
    return g


def load_profile(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig")) or {}
    if not isinstance(data, dict) or not isinstance(data.get("items"), list) or not data["items"]:
        raise ProfileError("profile needs a non-empty 'items' list")
    for i, it in enumerate(data["items"]):
        where = f"items[{i}]"
        if it.get("source") not in SOURCES:
            raise ProfileError(f"{where}: source must be one of {SOURCES}")
        if not it.get("kind") or not re.fullmatch(r"[A-Za-z0-9_-]+", str(it["kind"])):
            raise ProfileError(f"{where}: kind must be a simple word")
        if not it.get("files"):
            raise ProfileError(f"{where}: files is required")
        for g in it["files"]:
            safe_glob(g)
        if it["source"] == "regex":
            if not it.get("pattern"):
                raise ProfileError(f"{where}: regex source needs 'pattern'")
            bad = [f for f in it.get("flags", []) if f not in REGEX_FLAGS]
            if bad:
                raise ProfileError(f"{where}: unknown regex flags {bad} (use {list(REGEX_FLAGS)})")
        also = it.get("also_in")
        if also:
            for g in also.get("files", []):
                safe_glob(g)
    docs = data.get("docs") or {}
    for key in ("mention_globs", "exclude_globs", "ignore_globs"):
        for g in docs.get(key, []) or []:
            safe_glob(g)
    for kind, g in (docs.get("page_globs") or {}).items():
        safe_glob(g)
    allowed = set(CHECKS)
    unknown = [c for c in data.get("checks", []) or [] if c not in allowed]
    if unknown:
        raise ProfileError(f"unknown checks {unknown} (available: {sorted(allowed)})")
    return data


# ---------- extraction ----------

def text_of(v):
    if v is None or isinstance(v, (dict,)):
        return ""
    if isinstance(v, (list, tuple)):
        return ";".join(text_of(x) for x in v if not isinstance(x, (dict, list)))
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def render(template, values):
    if template is None:
        return ""
    out = TEMPLATE.sub(lambda m: text_of(values.get(m.group(1))), str(template))
    return " ".join(out.split())


def walk(obj, dotted):
    for part in str(dotted).split("."):
        if not part:
            continue
        obj = obj.get(part) if isinstance(obj, dict) else None
    return obj


def skip_reason(rules, values):
    for r in rules or []:
        v = values.get(r.get("field"))
        if "contains" in r:
            hit = (r["contains"] in v) if isinstance(v, (list, tuple)) else (str(r["contains"]) in text_of(v))
            if hit:
                return render(r.get("reason"), values) or str(r["contains"])
        if "equals" in r and text_of(v) == str(r["equals"]):
            return render(r.get("reason"), values) or str(r["equals"])
        if "matches" in r:
            m = re.search(r["matches"], text_of(v))
            if m:
                return render(r.get("reason"), values) or m.group(0)
    return ""


def records(spec, code):
    """Yield (values, source_path) for one items entry."""
    files = []
    for g in spec["files"]:
        files += [f for f in sorted(code.glob(g)) if f.is_file()]
    seen = set()
    for f in files:
        if f in seen:
            continue
        seen.add(f)
        rel = f.relative_to(code).as_posix()
        base = {"stem": f.stem, "path": rel, "file": f.name}
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        if spec["source"] == "regex":
            flags = 0
            for name in spec.get("flags", ["MULTILINE"]):
                flags |= REGEX_FLAGS[name]
            for m in re.finditer(spec["pattern"], text, flags):
                vals = dict(base)
                vals.update({k: (v or "") for k, v in m.groupdict().items()})
                vals.setdefault("name", m.group(1) if m.groups() else m.group(0))
                yield vals, rel
            continue
        try:
            data = json.loads(text) if spec["source"] == "json" else yaml.safe_load(text)
        except ValueError as e:
            sys.stderr.write(f"skip {rel}: {e}\n")
            continue
        if spec.get("each"):
            data = walk(data, spec["each"])
            rows = data if isinstance(data, list) else (list(data.values()) if isinstance(data, dict) else [])
        else:
            rows = data if isinstance(data, list) else [data]   # a top-level list is one item per entry
        for row in rows:
            vals = dict(base)
            if spec.get("unwrap") == "single-key" and isinstance(row, dict) and len(row) == 1:
                (key, row), = row.items()
                vals["key"] = key
            if isinstance(row, dict):
                for k, v in row.items():
                    vals.setdefault(k, v)
            yield vals, rel


def extract(profile, code):
    code = Path(code)
    items, seen = [], set()
    for spec in profile["items"]:
        expect = spec.get("expect") or {"mention": True}
        heading = expect.get("heading") or {}
        also = spec.get("also_in")
        also_names = None
        if also:
            also_names = set()
            for g in also.get("files", []):
                for f in sorted(code.glob(g)):
                    if f.is_file():
                        t = f.read_text(encoding="utf-8-sig", errors="replace")
                        also_names.update(m.group(1) for m in re.finditer(also["pattern"], t, re.M))
        for vals, rel in records(spec, code):
            item_id = render(spec.get("id", "{name}"), vals)
            if not item_id or (spec["kind"], item_id) in seen:
                continue
            seen.add((spec["kind"], item_id))
            vals["id"] = item_id
            row = {k: "" for k in FIELDS}
            row.update(kind=spec["kind"], id=item_id, name=render(spec.get("name", "{id}"), vals) or item_id,
                       aliases=render(spec.get("aliases", ""), vals), source_path=rel,
                       skip_reason=skip_reason(spec.get("skip_when"), vals))
            for col, tmpl in (spec.get("fields") or {}).items():
                if re.fullmatch(r"[A-Za-z0-9_]+", str(col)):
                    row[col] = render(tmpl, vals)
            if expect.get("page"):
                row["expected_page"] = render(expect["page"], vals)
                when = heading.get("when_field")
                if heading.get("text") and (not when or vals.get(when) not in (None, "", [], {})):
                    row["require_heading"] = heading["text"]
            if also:
                col = also.get("column", "also_in")
                aliases = [a for a in row["aliases"].split(";") if a]
                row[col] = "yes" if item_id in also_names else ("alias" if any(a in also_names for a in aliases) else "no")
            items.append(row)
    return items


def write_items(items, path):
    cols = list(FIELDS)
    for r in items:
        cols += [c for c in r if c not in cols]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(items)


# ---------- checks (fixed list; profiles can only name these) ----------

def _valkey_nav(docs, items_csv, out):
    import valkey_nav
    valkey_nav.main(docs, items_csv, out)


CHECKS = {"valkey_nav": _valkey_nav}


def run(profile_spec, code, docs, out):
    profile = load_profile(resolve_profile(profile_spec))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    items = extract(profile, code)
    write_items(items, out / "items.csv")
    d = profile.get("docs") or {}
    page_globs = [f"{k}={v}" for k, v in (d.get("page_globs") or {}).items()]
    # also_in with counts_as_documented: an item the docs don't mention but the code-side
    # reference file does (e.g. valkey.conf) is documented_elsewhere, not a gap.
    elsewhere = {}
    for spec in profile["items"]:
        also = spec.get("also_in") or {}
        if also.get("counts_as_documented"):
            elsewhere[spec["kind"]] = (also.get("column", "also_in"), ", ".join(also.get("files", [])))

    def adjust(r):
        rule = elsewhere.get(r["kind"])
        if rule and r["status"] == "not_mentioned" and r.get(rule[0]) in ("yes", "alias"):
            r["status"], r["detail"] = "documented_elsewhere", f"in {rule[1]}"
        return r

    rows, orphans = coverage.run(coverage.read_items([out / "items.csv"]), docs, out, page_globs,
                                 d.get("ignore_globs") or [], d.get("mention_globs") or ["**/*.md"],
                                 d.get("exclude_globs") or [], adjust=adjust)
    for name in profile.get("checks") or []:
        CHECKS[name](Path(docs), out / "items.csv", out)
    return profile, items, rows, orphans


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("profile")
    ap.add_argument("--code")
    ap.add_argument("--docs")
    ap.add_argument("--out", default="docs-coverage")
    ap.add_argument("--print-sparse", action="store_true", help="print the code paths to check out, one per line")
    a = ap.parse_args()
    try:
        if a.print_sparse:
            prof = load_profile(resolve_profile(a.profile))
            paths = (prof.get("code") or {}).get("sparse") or []
            for p in paths:
                safe_glob(p)
                print(p)
            sys.exit(0)
        if not (a.code and a.docs):
            ap.error("--code and --docs are required")
        prof, items, rows, orphans = run(a.profile, a.code, a.docs, a.out)
    except ProfileError as e:
        sys.exit(f"profile error: {e}")
    from collections import Counter
    sys.stderr.write(f"profile {prof.get('name', a.profile)}: {len(items)} items "
                     f"{dict(Counter(r['status'] for r in rows))}; orphan pages: {len(orphans)}; wrote {a.out}/\n")
