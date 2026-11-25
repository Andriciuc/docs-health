"""Tests for scripts/join_analytics.py. Run: python -m unittest discover -s tests"""

import csv
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import join_analytics as ja

PAGES = "path,title\nindex.md,Home\ninstall/apt.md,APT\nuntouched.md,Quiet\n"
# GA4-style export: a comment line, full URLs, version folders, a ratio column, a renamed URL.
ANALYTICS = """# GA4 export
Page path,Views,Average engagement time
https://docs.example.com/product/19/install/apt.html,100,10
/product/18/install/apt.html,300,30
/product/19/,50,5
/product/19/old-name.html,7,1
"""


def rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class JoinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = Path(tempfile.mkdtemp())
        (d / "pages.csv").write_text(PAGES, encoding="utf-8")
        (d / "ga.csv").write_text(ANALYTICS, encoding="utf-8")
        cls.out = d / "out" / "joined.csv"
        cls.log = StringIO()
        with redirect_stdout(cls.log):
            ja.main([str(d / "pages.csv"), str(d / "ga.csv"), "--out", str(cls.out)])
        cls.joined = {r["path"]: r for r in rows(cls.out)}

    def test_key_column_detected(self):
        self.assertIn("key='Page path'", self.log.getvalue())

    def test_counts_summed_across_versions(self):
        self.assertEqual(float(self.joined["install/apt.md"]["Views"]), 400)
        self.assertEqual(float(self.joined["index.md"]["Views"]), 50)

    def test_ratio_is_weighted_mean(self):
        # (10*100 + 30*300) / 400 = 25
        self.assertEqual(float(self.joined["install/apt.md"]["Average engagement time"]), 25)

    def test_no_traffic_is_blank(self):
        self.assertEqual(self.joined["untouched.md"]["Views"], "")

    def test_versions(self):
        by_ver = {(r["path"], r["version"]): float(r["Views"]) for r in rows(self.out.with_name("joined_by_version.csv"))}
        self.assertEqual(by_ver[("install/apt.md", "18")], 300)
        self.assertEqual(by_ver[("install/apt.md", "19")], 100)

    def test_unmatched_are_redirect_candidates(self):
        self.assertEqual([r["Page path"] for r in rows(self.out.with_name("unmatched.csv"))], ["/product/19/old-name.html"])

    def test_segs(self):
        self.assertEqual(ja.segs("https://x.y/a/b/?q=1#f"), ["a", "b", "index"])
        self.assertEqual(ja.segs("/a/b.html"), ["a", "b"])

    def test_empty_inputs_exit_cleanly(self):
        d = Path(tempfile.mkdtemp())
        (d / "p.csv").write_text("path,title\n", encoding="utf-8")
        (d / "a.csv").write_text(ANALYTICS, encoding="utf-8")
        with self.assertRaises(SystemExit):
            ja.main([str(d / "p.csv"), str(d / "a.csv"), "--out", str(d / "j.csv")])


if __name__ == "__main__":
    unittest.main()
