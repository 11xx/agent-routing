import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from routing_profiles import RouteRefusal, resolve, validate_selection


class SelectionUXTest(unittest.TestCase):
    def selection(self, **overrides):
        args = dict(profile_id="execute", backend="codex", model="gpt-6.1-sol",
                    effort="medium", provider="openai-codex", reason="operator directed")
        args.update(overrides)
        return validate_selection(ROOT, **args)

    def test_check_success_does_not_imply_a_seated_selection(self):
        check = subprocess.run([ROOT / "bin/routing-check", "gpt-6.1-sol", "medium"],
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0)
        with self.assertRaises(RouteRefusal) as caught:
            self.selection()
        self.assertEqual(caught.exception.payload()["seated_efforts"], ["xhigh"])
        self.assertIn("seated efforts", str(caught.exception))
        with self.assertRaises(RouteRefusal) as caught:
            self.selection(profile_id="execute", backend="claude", provider="anthropic",
                           model="opus-5.5", effort="medium")
        self.assertEqual(sorted(caught.exception.payload()["seated_efforts"]), ["high", "low"])

    def test_backend_spelling_and_named_tuple_cover_explicit_and_trial_tiers(self):
        for effort in ("low", "xhigh", "max"):
            command = [ROOT / "bin/validate-selection", "--profile", "implement",
                       "--backend", "claude", "--provider", "anthropic",
                       "--model", "claude-fable-5-2", "--effort", effort,
                       "--reason", "operator named this tuple", "--operator-named", "--json"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            selected = json.loads(result.stdout)
            self.assertEqual(selected["canonical_model"], "fable-5.2")
            self.assertEqual(selected["backend_model"], "claude-fable-5-2")
            self.assertEqual(selected["stability"], "experimental")
            self.assertTrue(selected["operator_named"])
        selected = self.selection(model="claude-sonnet-5-5", profile_id="implement",
                                  backend="claude", provider="anthropic", effort="max",
                                  operator_named=True)
        self.assertEqual(selected["canonical_model"], "sonnet-5.5")

    def test_named_tuple_preserves_bans_and_support(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.selection(model="gpt-6-astra", effort="max", operator_named=True)
        self.assertEqual(caught.exception.kind, "prohibited")
        with self.assertRaises(RouteRefusal) as caught:
            self.selection(backend="claude", provider="anthropic", model="gpt-6-astra",
                           effort="medium", operator_named=True)
        self.assertEqual(caught.exception.kind, "pool")

    def test_unsupported_profiles_name_read_only_alternatives_in_prose_and_json(self):
        for select in (lambda: self.selection(profile_id="generate", backend="claude",
                                             provider="anthropic", model="opus-5.5", effort="xhigh"),
                       lambda: resolve(ROOT, "generate", "claude")):
            with self.assertRaises(RouteRefusal) as caught:
                select()
            self.assertIn("explore:haiku", caught.exception.payload()["backend_routes"])
            self.assertIn("extract", str(caught.exception))
            self.assertIn("explore", str(caught.exception))
