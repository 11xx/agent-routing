"""Reviewer eligibility, the review frontier and quota-admitted review, over the fixture data."""

import unittest

from fixture import FIXTURE, edit, scratch

from quota_routing import admit_review
from routing_profiles import assess_review, data_problems, frontier_review
import stores

NOW = 2_000_000_000


def usage(northwind_five_hour):
    def window(remaining):
        return {"used_percentage": 100 - remaining, "remaining_percentage": remaining, "resets_at": NOW + 3600}
    return {"claude": {"state": "fresh", "updated_at": NOW, "five_hour": window(northwind_five_hour),
                       "seven_day": window(80)},
            "codex": {"state": "fresh", "updated_at": NOW, "seven_day": window(80)}}


def verdict(reviewer, author):
    answer = assess_review(FIXTURE, reviewer, [author])
    return answer["independence"], answer["clears"], answer["qualifiers"]


class AssessTest(unittest.TestCase):
    def test_another_lab_at_clearance_clears(self):
        """Claim: a reviewer from another lab at or above the clearance rank
        clears the work. Rejects refusing a valid independent review."""
        self.assertEqual(verdict("nw-atlas-2#xhigh", "ts-3-core#max"), ("eligible", True, []))

    def test_the_same_lineage_never_clears(self):
        """Claim: a reviewer from the author's own lineage is not independent.
        Rejects manufactured independence."""
        self.assertEqual(verdict("ts-3-prime#xhigh", "ts-3-core#max"), ("ineligible", False, ["same-family"]))

    def test_a_family_exception_clears_only_its_listed_authors(self):
        """Claim: a policy family exception lets its reviewer clear the authors
        it lists and no other model of that family. Rejects an exception that
        widens to the whole family."""
        self.assertEqual(verdict("nw-sage-2#high", "nw-atlas-2#medium")[:2], ("eligible", True))
        self.assertEqual(verdict("nw-atlas-2#xhigh", "nw-swift-2#high")[0], "ineligible")

    def test_a_reviewer_below_the_authors_floor_is_refused(self):
        """Claim: a reviewer ranked below the author's floor can neither find
        nor clear. Rejects a weak reviewer clearing strong work."""
        self.assertEqual(verdict("nw-swift-2#high", "ts-3-prime#xhigh"),
                         ("ineligible", False, ["below-floor", "below-clearance"]))

    def test_an_exception_reviewer_holding_a_review_seat_is_refused(self):
        """Claim: the validator refuses a family exception whose reviewer holds
        a review seat. Rejects an exception that would let the routine review
        seat clear its own family."""
        root = scratch(self)
        edit(root, stores.POLICY, 'reviewer = "nw-sage-2"', 'reviewer = "nw-atlas-2"')
        edit(root, stores.POLICY, 'authors = ["nw-atlas-2", "nw-swift-2"]', 'authors = ["nw-swift-2"]')
        self.assertIn("data/policy.toml [[family_exception]] reviewer=nw-atlas-2: reviewer holds a seat on the "
                      "review profile", data_problems(root))


    def test_schema_one_keeps_its_own_shape(self):
        """Claim: --schema 1 answers with exactly the agent-routing-assessment/1
        keys, without the purpose and clearance fields schema 2 adds. Rejects
        a schema-1 caller receiving a shape it cannot parse."""
        answer = assess_review(FIXTURE, "nw-atlas-2#xhigh", ["ts-3-core#max"], schema=1)
        self.assertEqual(sorted(answer), ["authors", "debt_kind", "floor", "independence", "qualifiers",
                                          "reviewer", "route_version", "schema"])
        self.assertEqual((answer["schema"], answer["independence"]), ("agent-routing-assessment/1", "eligible"))

class FrontierTest(unittest.TestCase):
    def test_the_frontier_is_the_strongest_independent_review_seat(self):
        """Claim: the frontier for an author is the highest-tier stable review
        seat that may review it, excluding its own lab's seats. Rejects a
        frontier that offers the author's own lab."""
        answer = frontier_review(FIXTURE, "ts-3-core#max")
        self.assertEqual(answer["frontier"]["seats"],
                         [{"backend": "claude", "effort": "xhigh", "model": "nw-atlas-2", "pool": "northwind-plan"}])


class AdmissionTest(unittest.TestCase):
    def test_a_codex_family_author_is_reviewed_on_the_claude_backend(self):
        """Claim: an author from a lineage admission lists as Codex-authored is
        reviewed through the claude backend while its window has headroom, and
        others through codex. Rejects a review routed into the author's pool."""
        admitted = admit_review(FIXTURE, "ts-3-core#max", usage(80), "base", "head", now=NOW)
        self.assertEqual((admitted["status"], admitted["route"]["backend"]), ("route", "claude"))
        other = admit_review(FIXTURE, "nw-atlas-2#medium", usage(80), "base", "head", now=NOW)
        self.assertEqual((other["status"], other["route"]["backend"]), ("route", "codex"))

    def test_a_window_at_the_threshold_returns_debt_not_a_route(self):
        """Claim: at or below the claude window threshold admission returns
        review debt with its reason. Rejects spending the scarce window's last
        headroom on review."""
        answer = admit_review(FIXTURE, "ts-3-core#max", usage(50), "base", "head", now=NOW)
        self.assertEqual((answer["status"], answer["reason"], answer["route"]),
                         ("review-debt", "claude-window-at-or-below-threshold", None))


if __name__ == "__main__":
    unittest.main()
