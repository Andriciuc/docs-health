"""Shared I/O guards for scanning repos that may not be trusted.

The workflows check out repos the caller names, including forks. Everything
read from them goes into CSVs, reports and Actions artifacts, so:

- files are only read if they resolve inside the folder being scanned
  (a symlink to ~/.ssh or /proc/self/environ is skipped, not followed);
- files over MAX_BYTES are skipped, so one huge file can't exhaust memory;
- CSV cells that a spreadsheet would run as a formula are neutralized;
- git never prompts for credentials and every subprocess has a timeout.
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

StrPath = str | os.PathLike[str]
if TYPE_CHECKING:
    _DictWriterBase = csv.DictWriter[str]
else:  # csv.DictWriter is only subscriptable at runtime from Python 3.12
    _DictWriterBase = csv.DictWriter

MAX_BYTES = int(os.environ.get("DOCS_HEALTH_MAX_FILE_BYTES", str(10 * 1024 * 1024)))
GIT_TIMEOUT = int(os.environ.get("DOCS_HEALTH_GIT_TIMEOUT", "900"))

# git must fail fast instead of waiting for a username on a private or missing repo.
GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS": "",
           "GCM_INTERACTIVE": "never"}

_warned: set[str] = set()


def warn(msg: str) -> None:
    if msg not in _warned:
        _warned.add(msg)
        print(f"warn: {msg}", file=sys.stderr)


def inside(path: StrPath, root: StrPath) -> bool:
    """True if path, after resolving symlinks, is root or below it."""
    try:
        return Path(path).resolve().is_relative_to(Path(root).resolve())
    except (OSError, RuntimeError):  # broken link, symlink loop
        return False


def contained(root: StrPath, rel: object) -> Path | None:
    """root / rel if it stays inside root, else None. For paths read from config files."""
    if rel is None:
        return None
    p = Path(root) / str(rel)
    return p if inside(p, root) else None


def readable(f: Path, root: StrPath) -> bool:
    """A regular file inside root and not larger than MAX_BYTES."""
    try:
        if not f.is_file():
            return False
        if not inside(f, root):
            warn(f"skipping {f}: resolves outside {root}")
            return False
        if f.stat().st_size > MAX_BYTES:
            warn(f"skipping {f}: larger than {MAX_BYTES} bytes (set DOCS_HEALTH_MAX_FILE_BYTES to change)")
            return False
    except OSError as e:
        warn(f"skipping {f}: {e}")
        return False
    return True


def files(root: StrPath, pattern: str) -> list[Path]:
    """Sorted files matching a glob under root, filtered by readable()."""
    root = Path(root)
    return [f for f in sorted(root.glob(pattern)) if readable(f, root)]


def rglob(root: StrPath, pattern: str) -> list[Path]:
    root = Path(root)
    return [f for f in sorted(root.rglob(pattern)) if ".git" not in f.parts and readable(f, root)]


def read_text(f: StrPath) -> str:
    return Path(f).read_text(encoding="utf-8-sig", errors="replace")


# ---------- CSV ----------
# Titles, headings, commit subjects and authors come from the scanned repos. A fork can set them
# to =HYPERLINK(...) or similar, which a spreadsheet runs when someone opens the CSV.
_FORMULA = ("=", "+", "-", "@", "\t", "\r")
_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?%?$")
_FLAG = re.compile(r"^--?[A-Za-z][A-Za-z0-9_.-]*(=[A-Za-z0-9_./:-]*)?$")   # --verbose, -p, --tls-port=6379


def cell(v: Any) -> Any:
    """Prefix a ' to text a spreadsheet would treat as a formula.
    Numbers and plain command-line flags are left alone: they can't call a function."""
    if isinstance(v, str) and v.startswith(_FORMULA) and not _NUMBER.match(v) and not _FLAG.match(v):
        return "'" + v
    return v


def uncell(v: Any) -> Any:
    """Undo cell() when reading our own CSVs back or displaying them."""
    if isinstance(v, str) and len(v) > 1 and v[0] == "'" and v[1] in "=+-@\t\r":
        return v[1:]
    return v


class DictWriter(_DictWriterBase):
    def writerow(self, rowdict: Mapping[str, Any]) -> Any:
        return super().writerow({k: cell(v) for k, v in rowdict.items()})

    def writerows(self, rowdicts: Iterable[Mapping[str, Any]]) -> None:
        for r in rowdicts:
            self.writerow(r)


class _Writer:
    def __init__(self, f: IO[str], **kw: Any) -> None:
        self._w = csv.writer(f, **kw)

    def writerow(self, row: Iterable[Any]) -> Any:
        return self._w.writerow([cell(v) for v in row])

    def writerows(self, rows: Iterable[Iterable[Any]]) -> None:
        for r in rows:
            self.writerow(r)


def writer(f: IO[str], **kw: Any) -> _Writer:
    return _Writer(f, **kw)


def read_csv(path: StrPath, **kw: Any) -> list[dict[str, Any]]:
    """Rows of one of our CSVs, with cell() undone."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k: uncell(v) for k, v in r.items()} for r in csv.DictReader(f, **kw)]
