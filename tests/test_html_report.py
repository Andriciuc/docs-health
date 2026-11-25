"""Tests for scripts/html_report.py. Run: python -m unittest discover -s tests"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import html_report


class HtmlReportTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "coverage_summary.md").write_text("# Summary\n\n| a | b |\n|---|---|\n| 1 | `x` |\n", encoding="utf-8")
        (self.d / "coverage-report.md").write_text(
            "# Main report\n\n- **11 pages lack `## Reply`**\n- [link](https://example.com)\n\n```\ncode <b>\n```\n",
            encoding="utf-8",
        )
        (self.d / "data.csv").write_text("id,n\nb,2\na,<10>\n", encoding="utf-8")
        (self.d / "lines.tsv").write_text("f\tl\nx.md\t3\n", encoding="utf-8")

    def test_page(self):
        page = html_report.build([self.d], "T", 5000)
        # main report first, then other markdown
        self.assertLess(page.index("Main report"), page.index("Summary"))
        self.assertIn("<strong>11 pages lack <code>## Reply</code></strong>", page)
        self.assertIn('<a href="https://example.com" rel="noopener noreferrer">link</a>', page)
        self.assertIn("code &lt;b&gt;", page)  # code is escaped
        self.assertIn("<td>&lt;10&gt;</td>", page)  # CSV cells are escaped
        self.assertIn("data.csv (2)", page)
        self.assertIn("lines.tsv (1)", page)
        self.assertNotRegex(page, r"=>|\blet |\bconst ")  # ES5 only

    def test_row_cap(self):
        page = html_report.build([self.d], "T", 1)
        self.assertIn("first 1 shown", page)


if __name__ == "__main__":
    unittest.main()
