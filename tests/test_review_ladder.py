"""Capability survives retirement, seating changes, and dated table reads."""

import copy
import json
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import routing_profiles as routing


def cli(*args):
    return subprocess.run([ROOT / "bin/agent-routing", *args], text=True, capture_output=True)


class OperatorClearanceDirectionTest(unittest.TestCase):

    def test_opus_high_clears_sol_xhigh_work_without_inheriting_its_reviewer_rank(self):
        author = routing.assess_review(ROOT, "opus-5.5#high", ["gpt-6.1-sol#xhigh"])
        reviewer = routing.assess_review(ROOT, "gpt-6.1-sol#xhigh", ["haiku-5.5#max"])
        self.assertGreater(reviewer["reviewer"]["review_tier"], author["authors"][0]["floor"])
        self.assertTrue(author["clears"])
        self.assertEqual(author["findings"], "eligible")
        self.assertIsNone(author["debt_kind"])


class CapabilityTest(unittest.TestCase):
    def test_a_known_default_effort_is_judgeable_without_a_reasoning_effort_order(self):
        answer = routing.assess_review(ROOT, "small-model-class#default", ["small-model-class#default"])
        self.assertEqual((answer["findings"], answer["clears"]), ("eligible", False))

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

    def test_same_family_equal_rank_finds_and_a_lower_effort_same_model_does_not(self):
        answer = routing.assess_review(ROOT, "fable-5.1#high", ["opus-5.5#high"])
        self.assertEqual((answer["findings"], answer["clears"]), ("eligible", False))
        answer = routing.assess_review(ROOT, "gpt-6.1-sol#high", ["gpt-6.1-sol#xhigh"])
        self.assertEqual(answer["findings"], "ineligible")

    def test_effortless_review_uses_minimum_rank_and_author_uses_maximum_floor(self):
        answer = routing.assess_review(ROOT, "claude-opus-5", ["gpt-6-luna#low"])
        self.assertEqual(answer["reviewer"]["review_tier"], 1)
        answer = routing.assess_review(ROOT, "gpt-6-astra#xhigh", ["claude-opus-5"])
        self.assertEqual(answer["authors"][0]["floor"], 2)


class DatedAssessmentTest(unittest.TestCase):
    def test_legacy_sol_reconstruction_keeps_top_review_rank_separate_from_author_floor(self):
        answer = routing.assess_review(ROOT, "gpt-6.1-sol#xhigh", ["gpt-6.1-sol#high"],
                                       as_of="2026-10-07T05:00:00Z")
        self.assertEqual((answer["reviewer"]["review_tier"], answer["floor"]), (3, 2))

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


class LadderExportTest(unittest.TestCase):
    def test_current_export_does_not_require_the_numeric_era_history(self):
        import review_ladder
        with patch.object(review_ladder, "commits", side_effect=ValueError("history is unavailable")):
            version, = review_ladder.export(ROOT)["version"]
        self.assertFalse(version["gap"])

    def test_current_export_has_one_complete_schema_fixed_version(self):
        result = cli("ladder", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        ladder = json.loads(result.stdout)
        self.assertEqual(ladder["schema"], "arc-review-ladder/1")
        version, = ladder["version"]
        self.assertFalse(version["gap"])
        for model in version["model"]:
            self.assertEqual(set(model), {"model", "identities", "family", "superseded", "efforts"})
            self.assertTrue(model["efforts"])
            for effort in model["efforts"]:
                self.assertEqual(set(effort), {"effort", "rank", "floor"})

    def test_history_starts_with_a_gap_and_deduplicates_capability_tables(self):
        result = cli("ladder", "--json", "--history")
        self.assertEqual(result.returncode, 0, result.stderr)
        versions = json.loads(result.stdout)["version"]
        self.assertEqual(versions[0]["effective_from"], "2026-08-01T00:00:00Z")
        self.assertTrue(versions[0]["gap"])
        self.assertNotIn("model", versions[0])
        self.assertEqual(versions[1]["effective_from"], "2026-10-07T04:51:04Z")
        self.assertIn("dc54196", versions[1]["source"])
        tables = [json.dumps(v["model"], sort_keys=True) for v in versions[1:]]
        self.assertTrue(all(a != b for a, b in zip(tables, tables[1:])))
        self.assertTrue(all("eras/" in v["source"] for v in versions[1:]))
        self.assertEqual(len({v["id"] for v in versions}), len(versions))


class LadderValidationTest(unittest.TestCase):
    def table(self):
        return [{"model": name, "identities": [name], "family": name, "superseded": False,
                 "efforts": [{"effort": "high", "rank": 2, "floor": 2}]} for name in ("a", "b")]

    def version(self):
        return {"id": "fixture-version", "effective_from": "2026-10-07T00:00:00Z", "source": "fixture evidence",
                "gap": False, "model": self.table()}

    def test_invalid_schema_tables_are_refused_with_the_version_named(self):
        import review_ladder
        for defect in ("floor", "rank", "empty", "identity", "date", "gap", "superseded"):
            version = self.version()
            if defect == "floor":
                version["model"][0]["efforts"][0]["floor"] = 3
            elif defect == "rank":
                version["model"][0]["efforts"][0]["rank"] = True
            elif defect == "empty":
                version["model"][0]["efforts"] = []
            elif defect == "identity":
                version["model"][0]["identities"] = ["b"]
            elif defect == "date":
                version["effective_from"] = "yesterday"
            elif defect == "gap":
                version["gap"] = True
            else:
                version["model"][0]["superseded"] = "false"
            with self.subTest(defect=defect), self.assertRaisesRegex(ValueError, "fixture-version"):
                review_ladder.validate({"schema": "arc-review-ladder/1", "version": [version]})

    def test_duplicate_version_ids_are_refused(self):
        import review_ladder
        second = self.version()
        second["effective_from"] = "2026-10-08T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "fixture-version.*unique"):
            review_ladder.validate({"schema": "arc-review-ladder/1", "version": [self.version(), second]})

    def test_an_invalid_historical_version_is_not_hidden_by_a_valid_current_table(self):
        import review_ladder
        manifest = {"model": [{"id": name, "family": name, "effort": [
            {"effort": "high", "review_tier": -1, "author_floor": 2}]} for name in ("a", "b")]}
        with patch.object(review_ladder, "commits", return_value=[("bad-revision", "2026-10-07T00:00:00Z")]), \
             patch.object(review_ladder, "historical_manifest", side_effect=lambda root, rev, name: manifest if name == "models" else {}), \
             patch.object(review_ladder, "source", return_value="fixture evidence"):
            with self.assertRaisesRegex(ValueError, "v-bad-revision.*rank"):
                review_ladder.export(ROOT, history=True)


if __name__ == "__main__":
    unittest.main()
