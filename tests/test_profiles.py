"""Tests for the profile engine (scripts/profile_coverage.py). Run: python -m unittest discover -s tests"""
import sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures" / "generic"
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts" / "checks")]
import profile_coverage as pc  # noqa: E402


def write_profile(text):
    p = Path(tempfile.mkdtemp()) / "p.yml"
    p.write_text(text, encoding="utf-8")
    return p


class GenericProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(tempfile.mkdtemp())
        _, cls.items, rows, cls.orphans = pc.run(str(FIX / "profile.yml"), FIX / "code", FIX / "docs", cls.out)
        cls.r = {(r["kind"], r["id"]): r for r in rows}

    def test_yaml_list_source(self):
        self.assertEqual(self.r[("setting", "cache.size")]["status"], "mentioned")
        self.assertEqual(self.r[("setting", "cache.ttl")]["status"], "skipped")
        self.assertEqual(self.r[("setting", "cache.ttl")]["skip_reason"], "internal")

    def test_deprecated_still_taught(self):
        row = self.r[("setting", "cache.mode")]
        self.assertEqual(row["deprecated_in_use"], "guides/config.md")   # replacement cache.policy not mentioned

    def test_regex_source_and_also_in(self):
        self.assertEqual(self.r[("flag", "--verbose")]["status"], "mentioned")
        self.assertEqual(self.r[("flag", "--dry-run")]["status"], "not_mentioned")
        self.assertEqual(self.r[("flag", "--dry-run")]["in_usage"], "yes")
        self.assertEqual(self.r[("flag", "--legacy")]["in_usage"], "no")

    def test_json_list_pages_and_headings(self):
        self.assertEqual(self.r[("endpoint", "list-users")]["status"], "documented")
        self.assertEqual(self.r[("endpoint", "list-users")]["name"], "GET list-users")
        self.assertEqual(self.r[("endpoint", "delete-user")]["status"], "undocumented")

    def test_orphans(self):
        self.assertEqual([o["page"] for o in self.orphans], ["reference/removed-endpoint.md"])

    def test_outputs(self):
        for f in ("items.csv", "coverage.csv", "orphans.csv", "coverage_summary.md"):
            self.assertTrue((self.out / f).exists(), f)


class ProfileSafetyTest(unittest.TestCase):
    def bad(self, text, msg):
        with self.assertRaises(pc.ProfileError) as cm:
            pc.load_profile(write_profile(text))
        self.assertIn(msg, str(cm.exception))

    def test_validation(self):
        item = "  - {kind: x, source: regex, files: [a.c], pattern: 'x'}\n"
        self.bad("items: []\n", "non-empty")
        self.bad("items:\n  - {kind: x, source: shell, files: [a]}\n", "source must be")
        self.bad("items:\n  - {kind: x, source: regex, files: [../etc/passwd], pattern: 'x'}\n", "relative")
        self.bad("items:\n  - {kind: x, source: regex, files: [/etc/passwd], pattern: 'x'}\n", "relative")
        self.bad("checks: [os.system]\nitems:\n" + item, "unknown checks")
        self.bad("docs: {mention_globs: ['../*']}\nitems:\n" + item, "relative")
        self.bad("items:\n  - {kind: x, source: regex, files: [a.c], pattern: 'x', flags: [VERBOSEX]}\n", "flags")

    def test_templates_only_substitute_fields(self):
        self.assertEqual(pc.render("{name.__class__} {name}", {"name": "a"}), "{name.__class__} a")
        self.assertEqual(pc.render("{container} {key}", {"key": "GET"}), "GET")

    def test_builtin_resolution(self):
        self.assertEqual(pc.resolve_profile("valkey").name, "valkey.yml")
        with self.assertRaises(pc.ProfileError):
            pc.resolve_profile("../valkey")
        with self.assertRaises(pc.ProfileError):
            pc.resolve_profile("nope")


if __name__ == "__main__":
    unittest.main()
