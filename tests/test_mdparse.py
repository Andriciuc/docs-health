"""Tests for scripts/mdparse.py. Run: python -m unittest discover -s tests"""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mdparse

DOC = "# Title\n\ntext\n\n```bash\n# not a heading\n```\n\n## Sub ##\n~~~\ncode\n~~~\n"


class MdparseTest(unittest.TestCase):
    def test_scan_kinds(self):
        kinds = [k for k, _ in mdparse.scan(DOC)]
        self.assertEqual(kinds, ["text", "text", "text", "text", "open", "code", "close", "text", "text",
                                 "open", "code", "close"])

    def test_headings_skip_fenced_code(self):
        self.assertEqual(mdparse.headings(DOC), [(1, "Title"), (2, "Sub")])

    def test_heading(self):
        self.assertEqual(mdparse.heading("### A b ###"), (3, "A b"))
        self.assertIsNone(mdparse.heading("#nospace"))


if __name__ == "__main__":
    unittest.main()
