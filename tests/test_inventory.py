"""Tests for scripts/inventory.py, run in-process on a small MkDocs repo with git history.
Run: python -m unittest discover -s tests"""

import csv
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(Path(__file__).resolve().parent)]
import fixture_repo
import inventory


def run(repo, *args):
    out = Path(tempfile.mkdtemp())
    with redirect_stdout(StringIO()):
        inventory.main([str(repo), "--out", str(out), *args])
    pages = {r["path"]: r for r in csv.DictReader(open(out / "pages.csv", encoding="utf-8"))}
    return out, pages, json.loads((out / "summary.json").read_text(encoding="utf-8"))


class InventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = fixture_repo.make_a()
        cls.out, cls.pages, cls.summary = run(cls.repo)

    def test_pages_and_urls(self):
        self.assertEqual(sorted(self.pages), ["guide/install.md", "index.md", "orphan.md", "snippets/note.md"])
        self.assertEqual(self.pages["index.md"]["url"], "https://example.com/t/")
        self.assertEqual(self.pages["guide/install.md"]["url"], "https://example.com/t/guide/install/")

    def test_titles_and_front_matter(self):
        self.assertEqual(self.pages["index.md"]["title"], "Home")
        self.assertIn("title", self.pages["index.md"]["front_matter_keys"])
        self.assertEqual(self.summary["pages_without_h1_or_title"], ["snippets/note.md"])

    def test_nav_placement_and_missing_file(self):
        self.assertEqual(self.pages["guide/install.md"]["nav:mkdocs.yml"], "Guide > Install")
        self.assertEqual(self.pages["guide/install.md"]["depth:mkdocs.yml"], "2")
        self.assertEqual(self.summary["per_config"]["mkdocs.yml"]["nav_missing_files"], ["guide/missing.md"])

    def test_orphans_exclude_snippets(self):
        self.assertEqual(self.summary["orphans_not_in_any_nav"], ["orphan.md"])
        self.assertEqual(self.pages["snippets/note.md"]["used_as_snippet"], "True")

    def test_links(self):
        self.assertEqual([b["target"] for b in self.summary["broken_internal"]], ["nope.md"])
        self.assertEqual(self.pages["guide/install.md"]["links_inbound"], "1")
        links = list(csv.DictReader(open(self.out / "links.csv", encoding="utf-8")))
        self.assertIn(
            {"page": "guide/install.md", "kind": "snippet", "target": "note.md", "scope": "internal", "status": "ok"}, links
        )

    def test_duplicates(self):
        self.assertEqual(self.summary["duplicate_paragraph_groups"], 1)
        dups = list(csv.DictReader(open(self.out / "duplicates.csv", encoding="utf-8")))
        self.assertEqual(sorted(d["page"] for d in dups), ["guide/install.md", "index.md"])

    def test_structure_and_type_guess(self):
        p = self.pages["guide/install.md"]
        self.assertEqual((p["ol_items"], p["code_blocks"]), ("2", "1"))
        self.assertTrue(p["type_guess"].startswith("task"))

    def test_git_history(self):
        self.assertEqual(self.pages["index.md"]["commits"], "1")
        self.assertEqual(self.pages["index.md"]["days_since_commit"], "0")

    def test_type_rule_overrides_guess(self):
        _, pages, _ = run(self.repo, "--type-rule", "guide/*.md=reference")
        self.assertEqual(pages["guide/install.md"]["type_guess"], "reference")

    def test_docs_dir_flag_without_config(self):
        _, pages, summary = run(self.repo, "--docs-dir", "docs", "--config", "none.yml")
        self.assertEqual(summary["pages"], 4)
        self.assertFalse(any(k.startswith("nav:") for k in pages["index.md"]))


if __name__ == "__main__":
    unittest.main()
