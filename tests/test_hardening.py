"""Hardening tests: untrusted repos must not leak files, exhaust memory or plant spreadsheet formulas.
Run: python -m unittest discover -s tests"""

import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts" / "checks")]
import docs_coverage
import profile_coverage as pc
import safeio

SECRET = "TOP-SECRET-OUTSIDE-THE-REPO"


def inventory(repo, *args):
    out = Path(tempfile.mkdtemp())
    r = subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts" / "inventory.py"), str(repo), "--out", str(out), *args],
        capture_output=True,
        text=True,
    )
    return r, out


def all_output(out):
    return "".join(p.read_text(encoding="utf-8", errors="replace") for p in out.rglob("*") if p.is_file())


class SymlinkTest(unittest.TestCase):
    def setUp(self):
        base = Path(tempfile.mkdtemp())
        self.outside = base / "outside"
        self.outside.mkdir()
        (self.outside / "secret.md").write_text(f"# {SECRET}\n\n{SECRET} " * 20, encoding="utf-8")
        self.repo = base / "repo"
        (self.repo / "docs").mkdir(parents=True)
        (self.repo / "docs" / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.repo / "docs" / "leak.md").symlink_to(self.outside / "secret.md")
        (self.repo / "docs" / "dir").symlink_to(self.outside, target_is_directory=True)

    def test_files_skips_links_out(self):
        names = [f.name for f in safeio.files(self.repo / "docs", "**/*.md")]
        self.assertEqual(names, ["index.md"])

    def test_inventory_does_not_read_outside(self):
        r, out = inventory(self.repo, "--docs-dir", "docs")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(SECRET, all_output(out))

    def test_link_inside_is_kept(self):
        (self.repo / "docs" / "alias.md").symlink_to(self.repo / "docs" / "index.md")
        self.assertIn("alias.md", [f.name for f in safeio.files(self.repo / "docs", "*.md")])


class ConfigEscapeTest(unittest.TestCase):
    def repo_with(self, mkdocs):
        repo = Path(tempfile.mkdtemp())
        (repo / "docs").mkdir()
        (repo / "docs" / "index.md").write_text("# Home\n", encoding="utf-8")
        (repo / "mkdocs.yml").write_text(mkdocs, encoding="utf-8")
        return repo

    def test_docs_dir_outside_refused(self):
        r, _ = inventory(self.repo_with("site_name: x\ndocs_dir: /etc\n"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("outside the repo", r.stderr)

    def test_inherit_outside_ignored(self):
        r, _ = inventory(self.repo_with("INHERIT: ../../../etc/passwd\nsite_name: x\n"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("outside the repo", r.stderr)

    def test_inherit_cycle_stops(self):
        repo = self.repo_with("INHERIT: mkdocs.yml\nsite_name: x\n")
        r, _ = inventory(repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("RecursionError", r.stderr)


class SizeCapTest(unittest.TestCase):
    def test_big_file_skipped(self):
        d = Path(tempfile.mkdtemp())
        (d / "big.md").write_bytes(b"x" * (safeio.MAX_BYTES + 1))
        (d / "ok.md").write_text("ok", encoding="utf-8")
        self.assertEqual([f.name for f in safeio.files(d, "*.md")], ["ok.md"])


class CsvFormulaTest(unittest.TestCase):
    def test_cells(self):
        for bad in ['=HYPERLINK("http://x","y")', "+cmd|' /C calc'!A0", "@SUM(1)", "-2+3+cmd|x!A0", "\t=1"]:
            self.assertTrue(safeio.cell(bad).startswith("'"), bad)
            self.assertEqual(safeio.uncell(safeio.cell(bad)), bad)
        for keep in ["-3", "+4.5", "12%", "--verbose", "-p", "--tls-port=6379", "plain", 7, None]:
            self.assertEqual(safeio.cell(keep), keep, keep)

    def test_writer_round_trip(self):
        p = Path(tempfile.mkdtemp()) / "x.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = safeio.DictWriter(f, fieldnames=["a"])
            w.writeheader()
            w.writerow({"a": "=1+1"})
        self.assertEqual(next(csv.reader(io.StringIO(p.read_text().splitlines()[1])))[0], "'=1+1")
        self.assertEqual(safeio.read_csv(p), [{"a": "=1+1"}])


class ExpectedPageTraversalTest(unittest.TestCase):
    def test_name_with_dotdot_is_not_read(self):
        base = Path(tempfile.mkdtemp())
        docs = base / "docs"
        docs.mkdir()
        (base / "outside.md").write_text("## Reply\n", encoding="utf-8")
        items = Path(tempfile.mkdtemp()) / "items.csv"
        with open(items, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["kind", "id", "name", "expected_page", "require_heading"])
            w.writeheader()
            w.writerow({"kind": "command", "id": "x", "name": "x", "expected_page": "../outside.md", "require_heading": "Reply"})
        rows, _ = docs_coverage.run(docs_coverage.read_items([items]), docs, Path(tempfile.mkdtemp()), [], [], ["**/*.md"], [])
        self.assertEqual(rows[0]["status"], "undocumented")


class ProfileValidationTest(unittest.TestCase):
    def load(self, text):
        p = Path(tempfile.mkdtemp()) / "p.yml"
        p.write_text(text, encoding="utf-8")
        return pc.load_profile(p)

    def test_bad_regex_is_a_profile_error(self):
        with self.assertRaisesRegex(pc.ProfileError, "invalid regex"):
            self.load("items:\n  - {kind: c, source: regex, files: ['*.c'], pattern: '(unclosed'}\n")

    def test_bad_skip_when_regex(self):
        with self.assertRaisesRegex(pc.ProfileError, "skip_when"):
            self.load("items:\n  - {kind: c, source: json, files: ['*.json'], skip_when: [{field: x, matches: '['}]}\n")

    def test_item_must_be_mapping(self):
        with self.assertRaisesRegex(pc.ProfileError, "mapping"):
            self.load("items:\n  - just-a-string\n")


class GitNoPromptTest(unittest.TestCase):
    def test_env(self):
        self.assertEqual(safeio.GIT_ENV["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(os.environ.get("PATH"), safeio.GIT_ENV.get("PATH"))


if __name__ == "__main__":
    unittest.main()
