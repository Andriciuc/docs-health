"""Tests for the code-coverage scripts. Run: python -m unittest discover -s tests

Fixtures in tests/fixtures/ are tiny copies of the Valkey formats (command JSON,
config.c, valkey.conf, valkey-doc layout). If an upstream format changes, update
the fixture first and watch which test breaks.
"""
import csv, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts" / "extract"), str(ROOT / "scripts" / "checks")]

import docs_coverage
import profile_coverage as pc
import valkey_nav


class CoverageTest(unittest.TestCase):
    """The built-in Valkey profile, run on the fixtures (same expectations as the
    old Valkey-only extractors, which the profile replaced)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        _profile, items, rows, cls.orphans = pc.run("valkey", FIX / "valkey", FIX / "docs", cls.tmp)
        cls.cfg = {r["id"]: r for r in items if r["kind"] == "config"}
        cls.rows = {r["id"]: r for r in rows}

    def test_command_statuses(self):
        self.assertEqual(self.rows["get"]["status"], "documented")
        self.assertEqual(self.rows["newcmd"]["status"], "undocumented")
        self.assertEqual(self.rows["acl-setrole"]["status"], "missing_heading")
        self.assertEqual(self.rows["internal"]["status"], "skipped")
        self.assertEqual(self.rows["acl-setrole"]["name"], "ACL SETROLE")

    def test_no_page_but_mentioned(self):
        # OLDMASTER has no page but is listed in bold in a topic
        self.assertEqual(self.rows["oldmaster"]["status"], "no_page_mentioned")

    def test_deprecated_in_use(self):
        # OLDCMD is mentioned next to its replacement GET: not flagged
        self.assertEqual(self.rows["oldcmd"]["deprecated_in_use"], "")
        # OLDMASTER's replacement NEWPRIMARY appears nowhere: flagged
        self.assertEqual(self.rows["oldmaster"]["deprecated_in_use"], "topics/guide.md")

    def test_config_extraction(self):
        self.assertEqual(set(self.cfg), {"daemonize", "databases", "tls-auth-clients-user", "secret-knob", "undocumented-knob"})
        self.assertEqual(self.cfg["secret-knob"]["skip_reason"], "HIDDEN_CONFIG")
        self.assertEqual(self.cfg["daemonize"]["in_conf"], "yes")
        self.assertEqual(self.cfg["tls-auth-clients-user"]["in_conf"], "yes")  # indented directive
        self.assertEqual(self.cfg["undocumented-knob"]["in_conf"], "no")
        self.assertEqual(self.cfg["undocumented-knob"]["aliases"], "old-knob")

    def test_config_mentions(self):
        self.assertEqual(self.rows["databases"]["status"], "mentioned")  # `databases 16`
        self.assertEqual(self.rows["daemonize"]["status"], "documented_elsewhere")   # in valkey.conf
        self.assertEqual(self.rows["undocumented-knob"]["status"], "not_mentioned")   # in neither

    def test_orphans(self):
        got = {o["page"]: o["reason"] for o in self.orphans}
        self.assertEqual(got, {"commands/orphan.md": "no_source", "commands/bf.add.md": "source_not_scanned"})

    def test_nav(self):
        out = self.tmp / "nav"
        valkey_nav.main(FIX / "docs", self.tmp / "items.csv", out)
        with open(out / "nav_coverage.csv", encoding="utf-8") as fh:
            nav = {r["id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(nav["get"]["status"], "covered")
        self.assertEqual(nav["get"]["level"], "group")
        self.assertEqual(nav["acl-setrole"]["level"], "container")
        self.assertEqual(nav["oldmaster"]["status"], "skipped")  # no page
        summary = (out / "nav_summary.md").read_text(encoding="utf-8")
        self.assertIn("'newgroup'", summary)  # missing from groups.json


class MentionIndexTest(unittest.TestCase):
    def test_index_matches_mentioned(self):
        pages = {"a.md": ([], {"sentinel master <name>", "maxmemory 2mb"}), "b.md": ([], {"sentinel", "port"})}
        index = docs_coverage.mention_index(pages)
        for name in ("sentinel", "sentinel master", "sentinel master <name>", "maxmemory", "max", "master", "port"):
            expected = {p for p, (_, spans) in pages.items() if docs_coverage.mentioned({name}, spans)}
            self.assertEqual(index.get(name, set()), expected, name)


if __name__ == "__main__":
    unittest.main()
