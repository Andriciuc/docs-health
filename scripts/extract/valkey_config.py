#!/usr/bin/env python3
"""Extract config options from Valkey src/config.c and check them against valkey.conf.

Usage:
  python valkey_config.py CONFIG_C [--conf valkey.conf] [--out items.csv]

Source of truth: the standardConfig table in config.c, i.e. calls like
  createBoolConfig("daemonize", NULL, IMMUTABLE_CONFIG, ...)
  createIntConfig("databases", NULL, IMMUTABLE_CONFIG, ...)
Name, alias and flags are read from the first three arguments.

valkey.conf is the self-documented config reference. An option counts as
present there when it appears as a directive, commented or not:
  "maxmemory <bytes>" / "# maxmemory <bytes>" / "# maxmemory-policy noeviction"

Output uses the common items format (see valkey_commands.py), kind=config,
with no expected_page: coverage.py then searches the docs for mentions.
skip_reason is HIDDEN_CONFIG / DEBUG_CONFIG / DEPRECATED_CONFIG when the flags
say the option isn't meant to be documented. Extra column in_conf says whether
valkey.conf documents it (yes/no/alias).
"""
import argparse, csv, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from valkey_commands import FIELDS  # noqa: E402

CALL = re.compile(r'create\w+Config\(\s*"([^"]+)"\s*,\s*(NULL|"[^"]*")\s*,\s*([A-Z_|\s]+?)\s*,', re.S)
SKIP_FLAGS = ("HIDDEN_CONFIG", "DEBUG_CONFIG", "DEPRECATED_CONFIG")


def conf_directives(conf_text):
    names = set()
    for line in conf_text.splitlines():
        # Any indentation: some directives are documented as "#   name VALUE".
        # Only membership of known names is tested, so extra prose words don't matter.
        m = re.match(r"^#?\s*([a-z][a-z0-9-]+)(\s|$)", line)
        if m:
            names.add(m.group(1))
    return names


def extract(config_c, conf=None):
    src = Path(config_c).read_text(encoding="utf-8", errors="replace")
    directives = conf_directives(Path(conf).read_text(encoding="utf-8", errors="replace")) if conf else None
    rows, seen = [], set()
    for m in CALL.finditer(src):
        name, alias, flags = m.group(1), m.group(2).strip('"'), " ".join(m.group(3).split())
        if alias == "NULL":
            alias = ""
        if name in seen:
            continue
        seen.add(name)
        skip = next((f for f in SKIP_FLAGS if f in flags), "")
        in_conf = ""
        if directives is not None:
            in_conf = "yes" if name in directives else ("alias" if alias and alias in directives else "no")
        rows.append({
            "kind": "config", "id": name, "name": name, "aliases": alias, "expected_page": "",
            "require_heading": "", "skip_reason": skip,
            "source_path": str(config_c), "group": flags, "container": "",
            "since": "", "deprecated_since": "", "replaced_by": "",
            "in_conf": in_conf,
        })
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config_c")
    ap.add_argument("--conf")
    ap.add_argument("--out", default="-")
    a = ap.parse_args()
    rows = extract(a.config_c, a.conf)
    fh = open(a.out, "w", newline="", encoding="utf-8") if a.out != "-" else sys.stdout
    w = csv.DictWriter(fh, fieldnames=FIELDS + ["in_conf"], extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    sys.stderr.write(f"{len(rows)} config options ({sum(1 for r in rows if r['skip_reason'])} hidden/debug/deprecated)\n")
