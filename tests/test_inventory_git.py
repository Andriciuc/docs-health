"""inventory.py: page history read from git.
Run: python -m unittest discover -s tests"""
import sys, tempfile, unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts"), str(Path(__file__).resolve().parent)]
import fixture_repo
from test_inventory import run


class NonAsciiPathTest(unittest.TestCase):
    def test_history_for_non_ascii_file_name(self):
        repo = Path(tempfile.mkdtemp())
        fixture_repo.write(repo, {"docs/cafÃ©.md": "# CafÃ©\n", "docs/index.md": "# Home\n"})
        fixture_repo.git(repo, "init", "-q")
        fixture_repo.git(repo, "add", "-A")
        fixture_repo.git(repo, "commit", "-qm", "init")
        _, pages, _ = run(repo, "--docs-dir", "docs")
        self.assertEqual(pages["cafÃ©.md"]["commits"], "1")
        self.assertEqual(pages["cafÃ©.md"]["days_since_commit"], "0")


if __name__ == "__main__":
    unittest.main()
