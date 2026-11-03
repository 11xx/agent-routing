"""Reads that find and reads that clear.

A review read answers two questions. `findings` asks whether its reviewer is
strong enough to be trusted with the defects it reports; `clears` asks whether
its approval may discharge review debt. A clearing read is family-independent
of every author and at or above both the author's floor and the manifest's
single clearance floor. A findings read reaches the author's floor, and a
same-family one only from strictly above it.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import routing_profiles  # noqa: E402
from routing_profiles import (  # noqa: E402
    RouteRefusal,
    assess_review,
    dumps,
    frontier_review,
    route_version,
    validation_problems,
)

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def fixture_root(case: unittest.TestCase) -> pathlib.Path:
    temporary = tempfile.TemporaryDirectory()
    case.addCleanup(temporary.cleanup)
    root = pathlib.Path(temporary.name)
    shutil.copytree(ROOT / "routing", root / "routing")
    return root


def run_assess(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([ROOT / "bin" / "agent-routing", "assess", *args], capture_output=True, text=True)


class ClearanceFloorTest(unittest.TestCase):
    """The manifest declares one clearance floor and validation holds it to that shape."""

    def rewrite_review(self, replacement: str) -> pathlib.Path:
        root = fixture_root(self)
        path = root / "routing" / "models.toml"
        text = path.read_text()
        self.assertIn("[review]\nclearance = 2\n", text)
        path.write_text(text.replace("[review]\nclearance = 2\n", replacement, 1))
        return root

    def test_the_manifest_declares_a_single_clearance_floor_of_two(self):
        # Rejects: a clearance threshold left to code, or declared per model.
        manifest = tomllib.loads((ROOT / "routing" / "models.toml").read_text())
        self.assertEqual(manifest["review"], {"clearance": 2})
        self.assertEqual(routing_profiles.clearance_floor(ROOT), 2)
        self.assertEqual(validation_problems(ROOT), [])

    def test_a_missing_or_malformed_clearance_floor_invalidates_the_manifest(self):
        # Rejects: a manifest without a usable floor that would clear every read.
        for replacement in ("", "[review]\n", "[review]\nclearance = 0\n", "[review]\nclearance = true\n",
                            '[review]\nclearance = "2"\n', "[review]\nclearance = 2\nfindings = 1\n"):
            with self.subTest(replacement=replacement):
                root = self.rewrite_review(replacement)
                self.assertTrue(any("clearance" in problem for problem in validation_problems(root)),
                                validation_problems(root))
                with self.assertRaises(RouteRefusal) as caught:
                    assess_review(root, "opus-5.5#xhigh", ["gpt-6.1-sol#low"])
                self.assertEqual(caught.exception.kind, "manifest-invalid")

    def test_the_floor_is_read_from_the_manifest_not_from_code(self):
        # Rejects: a hard-coded floor that ignores the declared value.
        root = self.rewrite_review("[review]\nclearance = 3\n")
        self.assertEqual(routing_profiles.clearance_floor(root), 3)
        answer = assess_review(root, "opus-5.5#xhigh", ["gpt-6.1-sol#low"])
        self.assertEqual((answer["clears"], answer["qualifiers"]), (False, ["below-clearance"]))


class AssessmentTwoAnswersTest(unittest.TestCase):
    def assess(self, reviewer, *authors, purpose=None, root=ROOT):
        if purpose is None:
            return assess_review(root, reviewer, list(authors))
        return assess_review(root, reviewer, list(authors), purpose=purpose)

    def answers(self, result):
        return {key: result[key] for key in ("independence", "findings", "clears", "qualifiers")}

    def test_a_cross_family_tier_one_read_finds_but_does_not_clear(self):
        # Rejects: a tier-1 cross-family read reported as clearing, or its
        # independence redefined away from its /1 meaning.
        result = self.assess("deepseek-flash#max", "gpt-6.1-sol#low")
        self.assertEqual(result["schema"], "agent-routing-assessment/2")
        self.assertEqual((result["purpose"], result["clearance"]), ("clearance", 2))
        self.assertEqual(self.answers(result), {
            "independence": "eligible", "findings": "eligible", "clears": False,
            "qualifiers": ["below-clearance"]})
        self.assertEqual(result["debt_kind"], "ineligible-review")

    def test_a_same_family_read_strictly_above_the_author_finds_but_never_clears(self):
        # Rejects: a same-family read treated as clearing, or refused as a
        # findings read when it sits above the author's floor.
        result = self.assess("gpt-6.1-sol#xhigh", "gpt-6.1-sol#low", purpose="findings")
        self.assertEqual(result["purpose"], "findings")
        self.assertEqual(self.answers(result), {
            "independence": "ineligible", "findings": "eligible", "clears": False,
            "qualifiers": ["same-model", "same-family"]})

    def test_a_same_family_read_at_the_author_floor_does_not_find(self):
        # Rejects: same-family findings eligibility at merely equal tier.
        result = self.assess("gpt-6.1-sol#xhigh", "gpt-6.1-sol#high", purpose="findings")
        self.assertEqual((result["findings"], result["clears"]), ("ineligible", False))
        result = self.assess("opus-5.5#xhigh", "sonnet-5.5#high", purpose="findings")
        self.assertEqual((result["findings"], result["clears"]), ("ineligible", False))

    def test_a_frontier_cross_family_read_clears(self):
        # Rejects: a clearing seat failing the new floor or losing its eligibility.
        result = self.assess("opus-5.5#xhigh", "gpt-6.1-sol#low")
        self.assertEqual(self.answers(result), {
            "independence": "eligible", "findings": "eligible", "clears": True, "qualifiers": []})
        self.assertIsNone(result["debt_kind"])

    def test_the_two_answers_do_not_depend_on_the_purpose_asked(self):
        # Rejects: the purpose silently changing what the read is.
        for reviewer, author in (("deepseek-flash#max", "gpt-6.1-sol#low"),
                                 ("gpt-6.1-sol#xhigh", "gpt-6.1-sol#low"),
                                 ("opus-5.5#xhigh", "gpt-6.1-sol#low")):
            with self.subTest(reviewer=reviewer):
                found = self.assess(reviewer, author, purpose="findings")
                cleared = self.assess(reviewer, author, purpose="clearance")
                self.assertEqual(self.answers(found), self.answers(cleared))
                self.assertEqual({**found, "purpose": None}, {**cleared, "purpose": None})

    def test_a_read_below_the_floor_unseated_or_against_an_unknown_floor_does_not_find(self):
        # Rejects: findings eligibility granted without an established tier comparison.
        self.assertEqual(self.assess("gpt-6.1-sol#xhigh", "opus-5.5#max")["findings"], "ineligible")
        self.assertEqual(self.assess("sonnet-5.5#high", "gpt-6.1-sol#low")["findings"], "ineligible")
        root = fixture_root(self)
        path = root / "routing" / "models.toml"
        path.write_text(path.read_text().replace("  author_floor = 4\n", "", 1))
        result = self.assess("gpt-6.1-sol#xhigh", "opus-5.5", root=root)
        self.assertEqual((result["findings"], result["clears"], result["qualifiers"]),
                         ("ineligible", False, ["floor-unknown"]))

    def test_every_same_family_author_must_sit_strictly_below_the_reader(self):
        # Rejects: the strict rule applied to the highest floor alone rather
        # than to each same-family author.
        result = self.assess("gpt-6-astra#xhigh", "gpt-6.1-sol#xhigh", "opus-5.5#low")
        self.assertEqual((result["findings"], result["clears"]), ("eligible", False))
        result = self.assess("gpt-6.1-sol#xhigh", "gpt-6.1-sol#low", "gpt-6.1-sol#high")
        self.assertEqual((result["findings"], result["clears"]), ("ineligible", False))

    def test_frontier_reads_keep_the_version_one_assessment(self):
        # Rejects: agent-routing-frontier/1 changing shape under its version.
        read, = frontier_review(ROOT, "gpt-6.1-sol#low", ["deepseek-flash#max"])["reads"]
        self.assertEqual(read["assessment"]["schema"], "agent-routing-assessment/1")
        self.assertNotIn("clears", read["assessment"])
        self.assertEqual(read["assessment"]["qualifiers"], [])


class AssessCliTest(unittest.TestCase):
    def test_json_defaults_to_version_two_and_carries_the_purpose(self):
        # Rejects: the CLI still emitting /1 by default, or ignoring --purpose.
        result = run_assess("--reviewer", "gpt-6.1-sol#xhigh", "--author", "gpt-6.1-sol#low",
                            "--purpose", "findings", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        answer = json.loads(result.stdout)
        self.assertEqual((answer["schema"], answer["purpose"], answer["findings"], answer["clears"]),
                         ("agent-routing-assessment/2", "findings", "eligible", False))
        self.assertIn("same-family", answer["qualifiers"])

    def test_the_text_line_answers_the_purpose_and_names_both_answers(self):
        # Rejects: a text line that reads "eligible" for a read that does not clear.
        result = run_assess("--reviewer", "deepseek-flash#max", "--author", "gpt-6.1-sol#low")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "does not clear: reviewer deepseek-flash#max (tier 1, clearance 2) against "
            "gpt-6.1-sol#low (floor 1); findings eligible; qualifiers below-clearance"])
        result = run_assess("--reviewer", "deepseek-flash#max", "--author", "gpt-6.1-sol#low",
                            "--purpose", "findings")
        self.assertTrue(result.stdout.startswith("findings eligible: "), result.stdout)
        self.assertIn("; does not clear;", result.stdout)

    def test_schema_one_output_is_byte_identical_to_the_version_one_contract(self):
        # Rejects: any change to the /1 bytes a pinned consumer parses. The
        # fixture holds the /1 answers with the route version and the roster's
        # identity lists, which are manifest data rather than shape, stripped.
        version = route_version(ROOT)
        for case in json.loads((FIXTURES / "assessment-v1.json").read_text()):
            arguments = ["--reviewer", case["reviewer"]]
            for author in case["authors"]:
                arguments += ["--author", author]
            with self.subTest(reviewer=case["reviewer"], authors=case["authors"]):
                result = run_assess(*arguments, "--schema", "1", "--json")
                self.assertEqual(result.returncode, 0, result.stderr)
                live = json.loads(result.stdout)
                expected = json.loads(json.dumps(case["json"]))
                expected["route_version"] = version
                expected["reviewer"]["identities"] = live["reviewer"]["identities"]
                for row, live_row in zip(expected["authors"], live["authors"], strict=True):
                    row["identities"] = live_row["identities"]
                self.assertEqual(result.stdout, dumps(expected) + "\n")
                text = run_assess(*arguments, "--schema", "1")
                self.assertEqual(text.stdout, case["text"])

    def test_version_one_cannot_answer_a_findings_question(self):
        # Rejects: /1 output that silently answers a different question than asked.
        result = run_assess("--reviewer", "deepseek-flash#max", "--author", "gpt-6.1-sol#low",
                            "--schema", "1", "--purpose", "findings", "--json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("agent-routing-assessment/1 answers clearance only", result.stderr)


if __name__ == "__main__":
    unittest.main()
