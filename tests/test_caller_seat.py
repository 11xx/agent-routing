import json
import pathlib
import subprocess
import sys
import unittest

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "lib"))
sys.path.insert(0, str(REPOSITORY / "tests"))
from roster import ROOT  # noqa: E402
from routing_profiles import RouteRefusal, resolve, validate_selection


class CallerSeatTest(unittest.TestCase):
    def validate(self, caller, caller_provider=None, **changes):
        values = dict(profile_id="explore", backend="codex", model="gpt-6-astra",
                      effort="xhigh", provider="openai-codex", reason="directed",
                      caller=caller, caller_provider=caller_provider)
        values.update(changes)
        return validate_selection(ROOT, **values)["confirmation"]

    def test_selection_above_luna_offers_the_named_route_and_pool(self):
        advisory = self.validate("gpt-6-luna#max", "openai-codex")
        self.assertTrue(advisory["advisory"])
        self.assertTrue(advisory["offer_to_user"])
        self.assertEqual(advisory["rank_comparison"], "above")
        self.assertEqual(advisory["reasons"], ["above-caller-seat"])
        self.assertEqual(advisory["selection"]["model"], "gpt-6-astra")
        self.assertEqual(advisory["selection"]["pool"], "the Codex subscription")
        self.assertTrue(advisory["benefit"])

    def test_same_and_lower_seats_are_ordinary(self):
        for profile, caller in (("review", "gpt-6.1-sol#xhigh"),
                                ("implement", "gpt-6-astra#xhigh")):
            advisory = resolve(ROOT, profile, "codex", caller=caller)["confirmation"]
            self.assertFalse(advisory["offer_to_user"])
            self.assertIn(advisory["rank_comparison"], ("same", "below"))

    def test_claude_pool_offers_even_without_cross_pool_ranks(self):
        advisory = resolve(ROOT, "explore", "claude", caller="gpt-6.1-sol#xhigh")["confirmation"]
        self.assertTrue(advisory["offer_to_user"])
        self.assertEqual(advisory["pool_comparison"], "scarcer")
        self.assertEqual(advisory["rank_comparison"], "unranked")
        self.assertEqual(advisory["reasons"], ["scarcer-pool"])

    def test_less_scarce_pool_does_not_establish_cross_pool_tier_cost(self):
        for caller in ("claude-opus-5-5#xhigh", "claude-haiku-5-5#high"):
            with self.subTest(caller=caller):
                advisory = resolve(ROOT, "review", "codex", caller=caller)["confirmation"]
                self.assertIsNone(advisory["offer_to_user"])
                self.assertEqual(advisory["pool_comparison"], "less-scarce")
                self.assertEqual(advisory["rank_comparison"], "unranked")
                self.assertEqual(advisory["reasons"], [])

    def test_unseated_effort_or_unordered_pool_does_not_invent_a_comparison(self):
        advisory = self.validate("gpt-6-astra#low")
        self.assertIsNone(advisory["offer_to_user"])
        self.assertEqual(advisory["rank_comparison"], "unranked")
        advisory = resolve(ROOT, "review", "codex", caller="deepseek-flash#max")["confirmation"]
        self.assertIsNone(advisory["offer_to_user"])
        self.assertEqual(advisory["pool_comparison"], "unranked")

    def test_ambiguous_pool_and_invalid_coordinates_are_refused(self):
        for caller, provider in (("gpt-6-luna#max", None), ("gpt-6-luna", "openai-codex"),
                                 ("missing#max", None), ("opus-5.5#missing", None),
                                 ("opus-5.5#xhigh", "openai-codex"), (None, "openai-codex")):
            with self.subTest(caller=caller, provider=provider), self.assertRaises(RouteRefusal):
                resolve(ROOT, "implement", "codex", caller=caller, caller_provider=provider)

    def test_no_caller_preserves_the_existing_response(self):
        self.assertNotIn("confirmation", resolve(ROOT, "implement", "codex"))

    def test_cli_both_verbs_accept_the_observed_seat(self):
        for command in (("resolve", "plan", "--variant", "astra-xhigh"),
                        ("validate", "--profile", "explore", "--model", "gpt-6-astra",
                         "--effort", "xhigh", "--provider", "openai-codex", "--reason", "directed")):
            result = subprocess.run([ROOT / "bin/agent-routing", *command, "--backend", "codex",
                                     "--caller", "gpt-6-luna#max", "--caller-provider", "openai-codex",
                                     "--json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["confirmation"]["offer_to_user"])
