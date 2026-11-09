"""lint-routing holds three relations over every roster row.

Each test copies the fixture tree, breaks one relation in one row, and runs
the lint there, so the failure is the one a roster edit would produce.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from roster import build  # noqa: E402


class LintRelationsTest(unittest.TestCase):
    def lint(self, old, new):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = build(pathlib.Path(temporary.name))
        path = root / "routing" / "models.toml"
        text = path.read_text()
        self.assertEqual(text.count(old), 1, old)
        path.write_text(text.replace(old, new))
        return subprocess.run([root / "bin" / "lint-routing"], capture_output=True, text=True)

    def assert_reported(self, result, problem):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(problem, result.stdout.splitlines())

    def test_a_rank_falling_as_effort_rises_is_reported(self):
        """Claim: a model whose deeper effort holds a lower review rank than a
        shallower one fails the lint, naming both tiers. Rejects a roster
        where max work could be reviewed below xhigh work of the same model."""
        tier = '  rank = {}\n  floor = 3\n  use = "prohibited: never select, including by explicit request, by operator'
        result = self.lint(tier.format(3), tier.format(1))
        self.assert_reported(result, "opus-5.5: rank falls from xhigh (2) to max (1)")

    def test_a_claude_cache_write_off_its_multiplier_is_reported(self):
        """Claim: a priced Claude row whose one-hour cache write is not twice
        its input price fails the lint. Rejects a Claude estimate that prices
        one-hour writes at a stale or missing rate."""
        result = self.lint("cache_write = 5.0, cache_write_1h = 8.0", "cache_write = 5.0, cache_write_1h = 6.0")
        self.assert_reported(result, "opus-5.5: cache_write_1h must be 2 times input (8), not 6.0")

    def test_a_codex_credit_rate_off_the_api_ratio_is_reported(self):
        """Claim: a Codex row whose credits are not 25 per API dollar of the
        same token class fails the lint. Rejects a credit rate left behind
        when the API price moved."""
        result = self.lint("subscription_credits_per_million = { input = 100.0, cached_input = 10.0, output = 500.0 }",
                           "subscription_credits_per_million = { input = 125.0, cached_input = 10.0, output = 500.0 }")
        self.assert_reported(result, "gpt-5.6-sol: input credits must be 25 per API dollar (100), not 125")


if __name__ == "__main__":
    unittest.main()
