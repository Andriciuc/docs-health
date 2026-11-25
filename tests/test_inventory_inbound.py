"""inventory.py: inbound link counts (links_inbound).
Run: python -m unittest discover -s tests"""
import sys, tempfile, unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts"), str(Path(__file__).resolve().parent)]
import fixture_repo
from test_inventory import run


class InboundLinkTest(unittest.TestCase):
    def test_directory_and_extensionless_links_count_as_inbound(self):
        repo = Path(tempfile.mkdtemp())
        fixture_repo.write(repo, {"docs/index.md": "# Home\n\n[dir](sub/) [page](sub/b) [anchor](sub/b.md#x)\n",
                                  "docs/sub/index.md": "# Sub\n", "docs/sub/b.md": "# B\n"})
        _, pages, _ = run(repo, "--docs-dir", "docs")
        self.assertEqual(pages["sub/index.md"]["links_inbound"], "1")
        self.assertEqual(pages["sub/b.md"]["links_inbound"], "2")


if __name__ == "__main__":
    unittest.main()
