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

import coverage  # noqa: E402
import valkey_commands  # noqa: E402
import valkey_config  # noqa: E402
import valkey_nav  # noqa: E402


class CoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cmds = valkey_commands.extract([FIX / "valkey" / "src" / "commands"])
        valkey_commands.write(cmds, cls.tmp / "cmds.csv")
        cfg = valkey_config.extract(FIX / "valkey" / "src" / "config.c", FIX / "valkey" / "valkey.conf")
        with open(cls.tmp / "cfg.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=valkey_commands.FIELDS + ["in_conf"])
            w.writeheader()
            w.writerows(cfg)
        cls.cfg = {r["id"]: r for r in cfg}
        items = coverage.read_items([cls.tmp / "cmds.csv", cls.tmp / "cfg.csv"])
        rows, cls.orphans = coverage.run(items, FIX / "docs", cls.tmp, ["command=commands/*.md"],
                                         ["commands/bf.*"], ["topics/*.md", "commands/*.md"], [])
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
        self.assertEqual(self.rows["daemonize"]["status"], "not_mentioned")

    def test_orphans(self):
        got = {o["page"]: o["reason"] for o in self.orphans}
        self.assertEqual(got, {"commands/orphan.md": "no_source", "commands/bf.add.md": "source_not_scanned"})

    def test_nav(self):
        out = self.tmp / "nav"
        valkey_nav.main(FIX / "docs", self.tmp / "cmds.csv", out)
        with open(out / "nav_coverage.csv", encoding="utf-8") as fh:
            nav = {r["id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(nav["get"]["status"], "covered")
        self.assertEqual(nav["get"]["level"], "group")
        self.assertEqual(nav["acl-setrole"]["level"], "container")
        self.assertEqual(nav["oldmaster"]["status"], "skipped")  # no page
        summary = (out / "nav_summary.md").read_text(encoding="utf-8")
        self.assertIn("'newgroup'", summary)  # missing from groups.json


if __name__ == "__main__":
    unittest.main()
