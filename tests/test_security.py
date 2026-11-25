"""Security regression tests. Run: python -m unittest discover -s tests"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import html_report


class LinkSafetyTest(unittest.TestCase):
    def test_script_urls_are_not_links(self):
        for bad in ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x", "vbscript:x"]:
            out = html_report.inline("[x](%s)" % bad)
            self.assertNotIn("<a ", out, bad)

    def test_attribute_breakout(self):
        out = html_report.inline('[x](foo"onmouseover=alert(1))')
        self.assertNotIn("<a ", out)
        self.assertNotIn('" onmouseover', out)

    def test_safe_links(self):
        self.assertIn('href="https://a.b/c?d=1&amp;e=2"', html_report.inline("[ok](https://a.b/c?d=1&e=2)"))
        self.assertIn('href="../topics/x.md#a"', html_report.inline("[r](../topics/x.md#a)"))

    def test_csv_and_markdown_are_escaped(self):
        page = html_report.md_to_html("# <script>x</script>\n\n| a |\n|---|\n| <img src=x onerror=1> |\n", "s")
        self.assertNotIn("<script>", page)
        self.assertNotIn("<img", page)


class RefSafetyTest(unittest.TestCase):
    def run_compare(self, a, b):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "compare.py"), a, b, "--work", "/tmp/dh-sec"], capture_output=True, text=True
        )

    def test_option_like_ref_refused(self):
        r = self.run_compare("owner/repo@--upload-pack=touch /tmp/x", "owner/repo@main")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("refusing unsafe ref", r.stderr + r.stdout)

    def test_odd_repo_refused(self):
        r = self.run_compare("owner/repo@main", "a;b/c@main")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
