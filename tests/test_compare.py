"""Tests for scripts/compare.py on two local trees that share git history.
Run: python -m unittest discover -s tests"""
import csv, sys, tempfile, unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(Path(__file__).resolve().parent)]
import compare
import fixture_repo


def rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class CompareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = fixture_repo.make_a()
        b = fixture_repo.make_b(a)
        cls.out = Path(tempfile.mkdtemp())
        with redirect_stdout(StringIO()):
            compare.main([str(a), str(b), "--out", str(cls.out), "--work", tempfile.mkdtemp()])

    def test_page_status(self):
        status = {(r["path_a"] or r["path_b"]): r["status"] for r in rows(self.out / "pages_compare.csv")}
        self.assertEqual(status, {"guide/install.md": "changed", "index.md": "same", "snippets/note.md": "same",
                                  "orphan.md": "only_a", "new.md": "only_b"})

    def test_nav(self):
        nav = {(r["status"], r["path"]) for r in rows(self.out / "nav_compare.csv")}
        self.assertEqual(nav, {("only_a", "guide/missing.md"), ("only_b", "new.md")})

    def test_issues_track_fixes(self):
        issues = {(r["issue"], r["where"], r["status"]) for r in rows(self.out / "issues_compare.csv")}
        self.assertIn(("broken_link", "index.md", "both"), issues)
        self.assertIn(("orphan", "orphan.md", "fixed_in_b"), issues)
        self.assertIn(("nav_missing_file", "mkdocs.yml", "fixed_in_b"), issues)

    def test_metrics(self):
        m = {r["metric"]: r for r in rows(self.out / "metrics_compare.csv")}
        self.assertEqual((m["orphans"]["a"], m["orphans"]["b"], m["orphans"]["delta"]), ("1", "0", "-1"))

    def test_commits_only_on_one_side(self):
        commits = rows(self.out / "commits_compare.csv")
        self.assertEqual([(c["side"], c["subject"]) for c in commits], [("only_b", "change")])

    def test_report_written(self):
        self.assertIn("new.md", (self.out / "compare.md").read_text(encoding="utf-8"))
        self.assertTrue((self.out / "a" / "pages.csv").exists() and (self.out / "b" / "pages.csv").exists())

    def test_unsafe_ref_refused(self):
        with self.assertRaises(SystemExit):
            compare.parse("owner/repo@-x")


class RenameSameTitleTest(unittest.TestCase):
    def test_same_title_picks_closest_text(self):
        base = Path(tempfile.mkdtemp())
        body = "Install the package, then start the service and check the logs for errors.\n" * 5
        fixture_repo.write(base / "a", {"docs/old/setup.md": "# Setup\n\n" + body})
        fixture_repo.write(base / "b", {"docs/a/setup.md": "# Setup\n\nSomething else entirely.\n",
                                        "docs/z/setup.md": "# Setup\n\n" + body})
        out = base / "out"
        with redirect_stdout(StringIO()):
            compare.main([str(base / "a"), str(base / "b"), "--out", str(out), "--work", str(base / "work"),
                          "--", "--docs-dir", "docs"])
        renamed = [(r["path_a"], r["path_b"]) for r in rows(out / "pages_compare.csv") if r["status"] == "renamed"]
        self.assertEqual(renamed, [("old/setup.md", "z/setup.md")])


if __name__ == "__main__":
    unittest.main()
