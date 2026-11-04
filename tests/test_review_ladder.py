"""Capability survives retirement, seating changes, and dated table reads."""

import copy
import json
import pathlib
import subprocess
import sys
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import routing_profiles as routing


def cli(*args):
    return subprocess.run([ROOT / "bin/agent-routing", *args], text=True, capture_output=True)


class CapabilityTest(unittest.TestCase):
    def test_every_known_effort_has_capability_even_without_a_seat(self):
        manifest = tomllib.loads((ROOT / "routing/models.toml").read_text())
        for model in manifest["model"]:
            for tier in model.get("effort", []):
                with self.subTest(model=model["id"], effort=tier["effort"]):
                    self.assertIs(type(tier.get("rank")), int)
                    self.assertIs(type(tier.get("floor")), int)
                    self.assertIn(tier["rank"], (1, 2, 3))
                    self.assertIn(tier["floor"], (1, 2, 3))

    def test_lint_rejects_missing_capability_and_an_exclusive_top(self):
        models = [{"id": "a", "family": "a", "effort": [{"effort": "high", "rank": 2, "floor": 2}]},
                  {"id": "b", "family": "b", "effort": [{"effort": "high", "rank": 2, "floor": 2}]}]
        for field, value in (("rank", None), ("floor", None), ("floor", 3), ("rank", True), ("floor", 4)):
            broken = copy.deepcopy(models)
            if value is None:
                del broken[0]["effort"][0][field]
            else:
                broken[0]["effort"][0][field] = value
            with self.subTest(field=field, value=value):
                self.assertTrue(routing.review_policy_problems(broken, [], {}))

    def test_unseated_astra_clears_and_keeps_only_a_routing_note(self):
        answer = routing.assess_review(ROOT, "gpt-6-astra#high", ["opus-5.5#high"])
        self.assertTrue(answer["clears"])
        self.assertEqual(answer["reviewer"]["review_tier"], 3)
        self.assertEqual(answer["qualifiers"], ["reviewer-unseated"])
        self.assertEqual(answer["independence"], "eligible")
        self.assertIsNone(answer["debt_kind"])

    def test_same_family_equal_rank_finds_and_a_lower_effort_same_model_does_not(self):
        answer = routing.assess_review(ROOT, "fable-5.1#high", ["opus-5.5#high"])
        self.assertEqual((answer["findings"], answer["clears"]), ("eligible", False))
        answer = routing.assess_review(ROOT, "gpt-6.1-sol#high", ["gpt-6.1-sol#xhigh"])
        self.assertEqual(answer["findings"], "ineligible")

    def test_retired_and_ledger_model_identities_remain_judgeable(self):
        manifest = tomllib.loads((ROOT / "routing/models.toml").read_text())
        by_id = {model["id"]: model for model in manifest["model"]}
        for model in ("gpt-5.6-sol", "gpt-6-sol", "opus-5", "fable-5"):
            self.assertTrue(by_id[model].get("superseded"), model)
            self.assertTrue(by_id[model]["effort"], model)
        for reviewer in ("gpt-5.6-sol#high", "gpt-6-sol#high", "claude-opus-5#medium",
                         "fable-5#high", "z-ai/glm-5.3-flash#max", "mimo-v2.6-pro#medium"):
            with self.subTest(reviewer=reviewer):
                answer = routing.assess_review(ROOT, reviewer, ["gpt-6-luna#low"])
                self.assertIsNotNone(answer["reviewer"]["review_tier"])

    def test_effortless_review_uses_minimum_rank_and_author_uses_maximum_floor(self):
        answer = routing.assess_review(ROOT, "claude-opus-5", ["gpt-6-luna#low"])
        self.assertEqual(answer["reviewer"]["review_tier"], 1)
        answer = routing.assess_review(ROOT, "gpt-6-astra#xhigh", ["claude-opus-5"])
        self.assertEqual(answer["authors"][0]["floor"], 2)


class DatedAssessmentTest(unittest.TestCase):
    def test_as_of_does_not_borrow_a_model_from_a_later_roster(self):
        args = ("assess", "--reviewer", "gpt-6.1-terra#medium", "--author", "opus-5.5#high", "--json")
        self.assertTrue(json.loads(cli(*args).stdout)["clears"])
        earlier = cli(*args, "--as-of", "2026-10-07T05:00:00Z")
        self.assertNotEqual(earlier.returncode, 0)
        self.assertEqual(earlier.stdout, "")
        self.assertIn("unknown reviewer coordinate", earlier.stderr)

    def test_as_of_reads_the_committed_table_and_keeps_assessment_two_shape(self):
        args = ("assess", "--reviewer", "gpt-6.1-sol#xhigh", "--author", "opus-5.5#high", "--json")
        old = cli(*args, "--as-of", "2026-10-07T05:00:00Z")
        self.assertEqual(old.returncode, 0, old.stderr)
        answer = json.loads(old.stdout)
        self.assertEqual(answer["schema"], "agent-routing-assessment/2")
        self.assertTrue(answer["clears"])
        self.assertNotEqual(answer["route_version"], routing.route_version(ROOT))
        same = cli(*args, "--as-of", "2026-10-07T02:00:00-03:00")
        self.assertEqual(same.stdout, old.stdout)

    def test_as_of_refuses_a_gap_and_an_invalid_instant_without_output(self):
        for instant, reason in (("2026-09-01T00:00:00Z", "ladder-gap"),
                                ("2026-10-07", "RFC 3339")):
            answer = cli("assess", "--reviewer", "gpt-6.1-sol#xhigh", "--author", "opus-5.5#high",
                         "--as-of", instant, "--json")
            self.assertNotEqual(answer.returncode, 0)
            self.assertEqual(answer.stdout, "")
            self.assertIn(reason, answer.stderr)


if __name__ == "__main__":
    unittest.main()
