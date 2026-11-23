#!/usr/bin/env python3
"""Extract documentable commands from Valkey command JSON (src/commands/*.json).

Usage:
  python valkey_commands.py SRC_COMMANDS_DIR [SRC_COMMANDS_DIR ...] [--out items.csv]

Each JSON file holds one command: {"NAME": {...}}. A subcommand has "container"
(e.g. ACL CAT lives in acl-cat.json with container "ACL"). The doc page for
<stem>.json is commands/<stem>.md, the same rule the website build uses
(valkey-io.github.io build/init-commands.sh).

Writes the common items format read by coverage.py:
  kind, id, name, aliases, expected_page, require_heading, skip_reason,
  source_path, group, container, since, deprecated_since, replaced_by
plus nothing else, so every extractor's output can be concatenated.

skip_reason is set for SYSCMD commands (internal, usually undocumented on purpose).
require_heading is "Reply" when the JSON has a reply_schema.
"""
import argparse, csv, json, sys
from pathlib import Path

FIELDS = ["kind", "id", "name", "aliases", "expected_page", "require_heading", "skip_reason",
          "source_path", "group", "container", "since", "deprecated_since", "replaced_by"]


def extract(dirs):
    rows = []
    for d in dirs:
        d = Path(d)
        for f in sorted(d.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8-sig"))
            except ValueError as e:
                sys.stderr.write(f"skip {f}: {e}\n")
                continue
            if not isinstance(data, dict) or len(data) != 1:
                continue
            (name, v), = data.items()
            container = v.get("container", "")
            full = f"{container} {name}" if container else name
            flags = v.get("doc_flags", [])
            rows.append({
                "kind": "command",
                "id": f.stem,
                "name": full,
                "aliases": "",
                "expected_page": f"commands/{f.stem}.md",
                "require_heading": "Reply" if "reply_schema" in v else "",
                "skip_reason": "SYSCMD" if "SYSCMD" in flags else "",
                "source_path": str(f),
                "group": v.get("group", ""),
                "container": container,
                "since": v.get("since", ""),
                "deprecated_since": v.get("deprecated_since", ""),
                "replaced_by": v.get("replaced_by", ""),
            })
    return rows


def write(rows, out):
    fh = open(out, "w", newline="", encoding="utf-8") if out != "-" else sys.stdout
    w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    if fh is not sys.stdout:
        fh.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", default="-")
    a = ap.parse_args()
    rows = extract(a.dirs)
    write(rows, a.out)
    sys.stderr.write(f"{len(rows)} commands\n")
