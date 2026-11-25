"""Tests for scripts/metadata_check.py. Run: python -m unittest discover -s tests"""
import sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures" / "meta"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tmp_root  # noqa: F401 - temp dirs go under one folder that is removed at exit
import metadata_check as mc


class MetadataCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pages, cls.prefixes = mc.run(FIX, ["topics/*.md"], "title", "description", 60, 70, 160, 3,
                                     short_words=1, template="Docs · {title}")
        cls.p = {Path(x["path"]).stem: x for x in pages}
        cls.issues = {k: set(filter(None, v["issues"].split(";"))) for k, v in cls.p.items()}

    def test_clean_page(self):
        self.assertEqual(self.issues["good"], set())       # H1 inside a code fence is ignored

    def test_short_title_and_body_h1(self):
        self.assertIn("short_title", self.issues["short"])
        self.assertIn("body_h1_with_title", self.issues["short"])
        self.assertNotIn("title_h1_mismatch", self.issues["short"])

    def test_duplicates(self):
        for k in ("short", "dup"):
            self.assertIn("duplicate_title", self.issues[k])
            self.assertIn("duplicate_description", self.issues[k])
            self.assertIn("short_description", self.issues[k])

    def test_no_front_matter(self):
        self.assertEqual(self.p["noh"]["title"], "First")
        self.assertIn("multiple_h1", self.issues["noh"])
        self.assertIn("missing_description", self.issues["noh"])

    def test_bom_and_mismatch(self):
        self.assertEqual(self.p["bom1"]["title"], "Search - Scoring")
        self.assertIn("title_h1_mismatch", self.issues["bom1"])

    def test_shared_prefix_and_template(self):
        for k in ("bom1", "p2", "p3"):
            self.assertIn("shared_prefix", self.issues[k])
        self.assertEqual(self.p["good"]["rendered_title"], "Docs · How to configure TLS for replication")
        self.assertEqual(self.p["good"]["title_len"], len("Docs · How to configure TLS for replication"))

    def test_write(self):
        out = Path(tempfile.mkdtemp())
        pages, prefixes = mc.run(FIX, ["topics/*.md"], "title", "description", 60, 70, 160, 3)
        mc.write(pages, prefixes, out, FIX, 3)
        self.assertIn("duplicate_title", (out / "metadata_summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
