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

    def test_inner_fence_of_other_kind_stays_code(self):
        doc = "~~~~markdown\n```\n# example heading\n```\n~~~~\n# Real\n"
        self.assertEqual([k for k, _ in mdparse.scan(doc)], ["open", "code", "code", "code", "close", "text"])
        self.assertEqual(mdparse.headings(doc), [(1, "Real")])

    def test_close_needs_same_length_and_nothing_after(self):
        doc = "````\n```\n``` python\n````\n# After\n"
        self.assertEqual([k for k, _ in mdparse.scan(doc)], ["open", "code", "code", "close", "text"])

    def test_heading(self):
        self.assertEqual(mdparse.heading("### A b ###"), (3, "A b"))
        self.assertIsNone(mdparse.heading("#nospace"))


if __name__ == "__main__":
    unittest.main()
