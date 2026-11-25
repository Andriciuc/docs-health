"""inventory.py: per-config nav checks.
Run: python -m unittest discover -s tests"""
import sys, tempfile, unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts"), str(Path(__file__).resolve().parent)]
import fixture_repo
from test_inventory import run


class DuplicateNavEntryTest(unittest.TestCase):
    def test_duplicate_nav_entries(self):
        repo = Path(tempfile.mkdtemp())
        fixture_repo.write(repo, {"mkdocs.yml": "site_name: T\nnav:\n  - index.md\n  - A: a.md\n  - Again: a.md\n  - B: b.md\n",
                                  "docs/index.md": "# Home\n", "docs/a.md": "# A\n", "docs/b.md": "# B\n"})
        _, _, summary = run(repo)
        self.assertEqual(summary["per_config"]["mkdocs.yml"]["dup_nav_entries"], ["a.md"])


if __name__ == "__main__":
    unittest.main()
