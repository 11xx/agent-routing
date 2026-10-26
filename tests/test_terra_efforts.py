"""Terra's directed implementation tiers and prohibition."""

import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from routing_profiles import RouteRefusal, resolve, validate_selection


class TerraEffortsTest(unittest.TestCase):
    def test_stable_implementation_variants(self):
        for effort in ("medium", "high", "xhigh"):
            with self.subTest(effort=effort):
                route = resolve(ROOT, "implement", "codex", variant_id="terra-" + effort)
                self.assertEqual((route["model"], route["effort"], route["stability"]),
                                 ("gpt-6.1-terra", effort, "stable"))
                selected = validate_selection(ROOT, profile_id="implement", backend="codex",
                                              model="gpt-6.1-terra", effort=effort,
                                              provider="openai-codex", reason="directed")
                self.assertEqual(selected["stability"], "stable")

    def test_low_requires_explicit_selection_and_max_is_prohibited(self):
        args = dict(profile_id="implement", backend="codex", model="gpt-6.1-terra",
                    provider="openai-codex", reason="directed")
        with self.assertRaises(RouteRefusal):
            validate_selection(ROOT, effort="low", **args)
        result = validate_selection(ROOT, effort="low", operator_named=True, **args)
        self.assertEqual(result["effort"], "low")
        with self.assertRaises(RouteRefusal):
            validate_selection(ROOT, effort="max", operator_named=True, **args)
        check = subprocess.run([ROOT / "bin/routing-check", "gpt-6.1-terra", "max"],
                               capture_output=True, text=True)
        self.assertNotEqual(check.returncode, 0)
        self.assertIn("prohibited", check.stdout + check.stderr)
