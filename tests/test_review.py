"""Reviewer eligibility, the review frontier and quota-admitted review, over the fixture data."""

import unittest

from fixture import FIXTURE, edit, scratch

from quota_routing import admit_review
from routing_profiles import RouteRefusal, assess_review, data_problems, frontier_review, resolve
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

    def test_schema_one_refuses_a_findings_purpose(self):
        """Claim: --schema 1 with --purpose findings is refused as
        invalid-purpose. Rejects a schema-1 answer, which carries
        independence alone, standing in for a findings read."""
        with self.assertRaises(RouteRefusal) as caught:
            assess_review(FIXTURE, "nw-atlas-2#xhigh", ["ts-3-core#max"], schema=1, purpose="findings")
        self.assertEqual(caught.exception.kind, "invalid-purpose")

    def test_an_unseated_reviewer_is_marked_and_still_clears(self):
        """Claim: a reviewer no review seat holds carries the informational
        reviewer-unseated qualifier, and it neither blocks independence nor
        clearance. Rejects hiding that the reviewer holds no seat, or letting
        that fact refuse a read the floors allow."""
        answer = assess_review(FIXTURE, "nw-sage-2#medium", ["ts-3-core#max"])
        self.assertEqual((answer["qualifiers"], answer["independence"], answer["clears"]),
                         (["reviewer-unseated"], "eligible", True))

    def test_findings_and_clearance_are_separate_answers(self):
        """Claim: a same-family reviewer above the author's floor finds but
        never clears, and the answers do not depend on the purpose asked.
        Rejects a same-family read clearing debt, or a findings read refused
        because it cannot clear."""
        for purpose in ("clearance", "findings"):
            with self.subTest(purpose=purpose):
                answer = assess_review(FIXTURE, "nw-atlas-2#xhigh", ["nw-swift-2#high"], purpose=purpose)
                self.assertEqual((answer["findings"], answer["clears"], answer["purpose"]),
                                 ("eligible", False, purpose))

    def test_the_same_model_at_a_lower_effort_neither_finds_nor_clears(self):
        """Claim: the author's own model at a lower effort is refused for both
        purposes, and at an equal or higher effort it finds without clearing.
        Rejects the author's model at a cheaper effort standing in for review."""
        lower = assess_review(FIXTURE, "nw-atlas-2#medium", ["nw-atlas-2#high"])
        self.assertEqual((lower["findings"], lower["clears"], lower["qualifiers"]),
                         ("ineligible", False, ["same-model", "same-family"]))
        higher = assess_review(FIXTURE, "nw-atlas-2#xhigh", ["nw-atlas-2#high"])
        self.assertEqual((higher["findings"], higher["clears"]), ("eligible", False))

    def test_several_authors_take_the_highest_floor_and_every_qualifier(self):
        """Claim: a diff with several authors is judged against the highest
        author floor, and any author from the reviewer's lineage makes the
        read ineligible. Rejects judging a mixed diff by its weakest or its
        last author."""
        mixed = assess_review(FIXTURE, "ts-3-prime#xhigh", ["orbit-flash#max", "nw-atlas-2#high"])
        self.assertEqual((mixed["floor"], mixed["independence"], mixed["clears"]), (2, "eligible", True))
        own = assess_review(FIXTURE, "ts-3-prime#xhigh", ["ts-3-core#max", "nw-atlas-2#high"])
        self.assertEqual((own["floor"], own["independence"], own["qualifiers"]), (2, "ineligible", ["same-family"]))

    def test_an_omitted_effort_takes_the_author_maximum_and_the_reviewer_minimum(self):
        """Claim: an author named without an effort is judged at its highest
        floor across tiers, and a reviewer without one at its lowest review
        tier. Rejects an omitted effort read in whichever direction clears."""
        author = assess_review(FIXTURE, "ts-3-prime#high", ["nw-atlas-2"])
        self.assertEqual((author["floor"], author["independence"]), (3, "ineligible"))
        self.assertEqual(assess_review(FIXTURE, "ts-3-prime#xhigh", ["nw-atlas-2"])["clears"], True)
        reviewer = assess_review(FIXTURE, "ts-3-prime", ["nw-atlas-2#high"])
        self.assertEqual((reviewer["reviewer"]["review_tier"], reviewer["clears"]), (1, False))


def review_seat(purpose, backend, model, effort, family="any"):
    return {"purpose": purpose, "author_family": family, "backend": backend, "model": model, "effort": effort,
            "when": "A fixture read.", "why": "A fixture reason.", "since": "2030-01-09"}


def change_policy(root, change):
    """Rewrite the policy store after `change` edits its parsed tables."""
    path = root / stores.POLICY
    document = stores.parse_toml(path.read_text(), stores.POLICY)
    change(document)
    path.write_text(stores.emit_policy(document))


def change_catalog(root, change):
    """Rewrite the catalog store after `change` edits its parsed tables."""
    path = root / stores.CATALOG
    document = stores.parse_toml(path.read_text(), stores.CATALOG)
    change(document)
    path.write_text(stores.emit_catalog(document))


def drop_review_seat(document, purpose, backend, family="any"):
    rows = document["review_seat"]
    rows.remove(next(row for row in rows if (row["purpose"], row["backend"], row["author_family"])
                     == (purpose, backend, family)))


def seat_row(variant, backend, provider, model, effort):
    return {"profile": "review", "variant": variant, "backends": [backend], "provider": provider, "model": model,
            "effort": effort, "stability": "stable", "when": "A fixture read.", "why": "A fixture reason.",
            "since": "2030-01-09"}


class ReviewSeatValidationTest(unittest.TestCase):
    WHERE = "data/policy.toml [[review_seat]] purpose="

    def test_a_row_that_can_never_satisfy_its_purpose_is_named(self):
        """Claim: the validator names, by its row, a review seat that can
        never serve its purpose: a clearance seat in the lab of the authors it
        is for, a clearance seat below the clearance floor, and an exhaustive
        seat below its backend's highest-ranked review route. Rejects a policy
        whose review seat could only ever refuse, or be sold for a purpose it
        cannot meet."""
        root = scratch(self)

        def change(document):
            document["seat"].append(seat_row("core", "codex", "tessel-plan", "ts-3-core", "max"))
            drop_review_seat(document, "exhaustive", "codex")
            document["review_seat"] += [review_seat("clearance", "codex", "ts-3-prime", "xhigh", "tessel"),
                                        review_seat("clearance", "pi", "orbit-flash", "max"),
                                        review_seat("exhaustive", "codex", "ts-3-core", "max")]
        change_policy(root, change)
        self.assertEqual(sorted(data_problems(root)), [
            f"{self.WHERE}clearance author_family=any backend=pi: rank 1 is below the [review] clearance floor 2, "
            "which a clearance seat must meet",
            f"{self.WHERE}clearance author_family=tessel backend=codex: the seat shares the lab tessel of the "
            "authors it is for, so it can never clear them",
            f"{self.WHERE}exhaustive author_family=any backend=codex: rank 2 is below the highest-ranked review "
            "route on backend 'codex' (rank 3); an exhaustive seat must be among them"])

    def test_a_row_names_a_stable_review_route_on_its_backend(self):
        """Claim: a review seat must name a stable route of the review profile
        on its backend, so removing that route or naming another backend's
        model is refused by the row. Rejects a seat resolve could never
        dispatch."""
        root = scratch(self)
        change_policy(root, lambda document: document["review_seat"].append(
            review_seat("findings", "codex", "ts-3-core", "max", "orbit")))
        self.assertEqual(data_problems(root), [f"{self.WHERE}findings author_family=orbit backend=codex: ts-3-core "
                                               "max is no stable route of the review profile on backend 'codex'"])

    def test_a_clearance_seat_is_feasible_only_for_labs_it_can_clear(self):
        """Claim: an any clearance seat is judged against the authors outside
        its own lab, so one whose only reachable floors are its own lab's is
        named, though those low floors would let it pass. Rejects a seat that
        can clear no lab's authors validating on floors it may never review."""
        root = scratch(self)
        change_catalog(root, lambda document: [tier.update(floor=3) for tier in document["tier"]
                                               if tier["model"].startswith(("nw-", "orbit-"))])

        def change(document):
            document["seat"].append(seat_row("core", "codex", "tessel-plan", "ts-3-core", "max"))
            next(row for row in document["review_seat"]
                 if (row["purpose"], row["backend"]) == ("clearance", "codex")).update(model="ts-3-core", effort="max")
        change_policy(root, change)
        self.assertIn(f"{self.WHERE}clearance author_family=any backend=codex: rank 2 is below every floor of the "
                      "authors outside its lab (the least is 3), so it can never clear them", data_problems(root))

    def test_coverage_counts_only_seats_that_can_clear_the_lab(self):
        """Claim: removing the only clearance seat able to reach a lab's
        floors is named, though seats outside that lab remain on every
        backend. Rejects a policy in which a lab's authors are refused on
        every backend while the validator calls them served."""
        root = scratch(self)
        change_catalog(root, lambda document: [tier.update(floor=3) for tier in document["tier"]
                                               if tier["model"].startswith("orbit-")])

        def change(document):
            document["seat"] += [seat_row("core", "codex", "tessel-plan", "ts-3-core", "max"),
                                 seat_row("atlas-high", "claude", "northwind-plan", "nw-atlas-2", "high")]
            for row in document["review_seat"]:
                if row["purpose"] == "clearance":
                    row.update(model="ts-3-core", effort="max") if row["backend"] == "codex" else row.update(
                        model="nw-atlas-2", effort="high")
            document["review_seat"].append(review_seat("clearance", "codex", "ts-3-prime", "xhigh", "orbit"))
        change_policy(root, change)
        self.assertEqual(data_problems(root), [])
        self.assertEqual(resolve(root, "review", "codex", author="orbit-flash#max")["review"]["clears"], True)
        change_policy(root, lambda document: drop_review_seat(document, "clearance", "codex", "orbit"))
        self.assertEqual(data_problems(root), [f"{self.WHERE}clearance: lab orbit has seated authors and no "
                                               "clearance seat outside it at or above the least of their floors"])

    def test_a_lab_with_seated_authors_keeps_a_clearance_seat_outside_it(self):
        """Claim: once no clearance seat outside a lab can serve it, the
        validator names that lab when one of its models holds a seat outside
        review. Rejects a policy that leaves a lab's authored work no
        independent reader at all."""
        self.assertEqual(data_problems(FIXTURE), [])
        root = scratch(self)
        change_policy(root, lambda document: drop_review_seat(document, "clearance", "claude"))
        self.assertEqual(data_problems(root), [f"{self.WHERE}clearance: lab tessel has seated authors and no "
                                               "clearance seat outside it at or above the least of their floors"])


CLOSED_QUALIFIERS = {"same-model", "same-family", "below-floor", "below-clearance", "floor-unknown",
                     "reviewer-unseated"}


def with_review_variant(test, variant, backend, provider, model, effort, *rows):
    """A scratch policy with one more stable review route and the given review seats."""
    root = scratch(test)

    def change(document):
        document["seat"].append(seat_row(variant, backend, provider, model, effort))
        document["review_seat"] += list(rows)
    change_policy(root, change)
    test.assertEqual(data_problems(root), [])
    return root


class ReviewPurposeTest(unittest.TestCase):
    def refusal(self, root, *args, **options):
        with self.assertRaises(RouteRefusal) as caught:
            resolve(root, *args, **options)
        return caught.exception.payload()

    def test_clearance_answers_the_row_for_the_authors_lab_and_refuses_one_below_its_floor(self):
        """Claim: clearance answers the review seat the policy names for the
        author's lab, else its any seat, and refuses with the floor rule
        when that seat ranks below the author's floor. Rejects a clearance
        reader picked by rank instead of by the written seat, or a seat
        sold to an author it cannot clear."""
        row = review_seat("clearance", "claude", "nw-atlas-2", "high", "orbit")
        root = with_review_variant(self, "atlas-high", "claude", "northwind-plan", "nw-atlas-2", "high", row)
        chosen = resolve(root, "review", "claude", author="orbit-flash#max")
        self.assertEqual((chosen["profile"], chosen["effort"], chosen["review"]["clears"]),
                         ("review:atlas-high", "high", True))
        self.assertEqual(resolve(root, "review", "claude", author="ts-3-core#max")["profile"], "review:atlas")
        change_policy(root, lambda document: document["review_seat"].__setitem__(
            1, {**document["review_seat"][1], "effort": "high"}))
        self.assertEqual(data_problems(root), [])
        self.assertEqual(resolve(root, "review", "claude", author="ts-3-core#max")["profile"], "review:atlas-high")
        refused = self.refusal(root, "review", "claude", author="ts-3-prime#max")
        self.assertEqual((refused["kind"], refused["reason"], refused["author_tier"], refused["purpose"]),
                         ("review-independence", "no-eligible-route", 3, "clearance"))
        self.assertIn("at or above author 'ts-3-prime#max' and at or above clearance floor 2", refused["message"])

    def test_findings_answers_the_route_its_row_names_over_the_default(self):
        """Claim: findings answers the route its review seat names, though
        the backend's default review route would also serve the author.
        Rejects findings chosen by the profile default rather than by the
        policy's row."""
        root = with_review_variant(self, "core", "codex", "tessel-plan", "ts-3-core", "max")
        self.assertEqual(resolve(root, "review", "codex", author="orbit-flash#max", purpose="findings")["profile"],
                         "review")
        change_policy(root, lambda document: next(
            row for row in document["review_seat"] if (row["purpose"], row["backend"]) == ("findings", "codex")
        ).update(model="ts-3-core", effort="max"))
        self.assertEqual(data_problems(root), [])
        found = resolve(root, "review", "codex", author="orbit-flash#max", purpose="findings")
        self.assertEqual((found["profile"], found["model"], found["effort"], found["review"]["findings"]),
                         ("review:core", "ts-3-core", "max", "eligible"))

    def test_findings_refuses_its_seat_for_the_same_model_above_its_effort(self):
        """Claim: findings answers its seat for an author of the seat's own
        lab, and refuses it for the seat's own model at a higher effort.
        Rejects a cheaper effort of the author's model standing in for a
        findings read."""
        found = resolve(FIXTURE, "review", "claude", author="nw-atlas-2#high", purpose="findings")
        self.assertEqual((found["model"], found["review"]["findings"], found["review"]["clears"]),
                         ("claude-atlas-2", "eligible", False))
        refused = self.refusal(FIXTURE, "review", "claude", author="nw-atlas-2#max", purpose="findings")
        self.assertEqual((refused["kind"], refused["reason"], refused["purpose"]),
                         ("review-independence", "no-eligible-route", "findings"))

    def test_exhaustive_answers_the_top_ranked_seat_and_refuses_a_lower_one(self):
        """Claim: an exhaustive read answers the backend's exhaustive seat,
        which ranks with its highest-ranked review route, refuses a named
        variant ranked below it, and refuses a backend with no exhaustive
        seat. Rejects an exhaustive read from a weaker reader than the
        backend offers."""
        root = with_review_variant(self, "core", "codex", "tessel-plan", "ts-3-core", "max")
        top = resolve(root, "review", "codex", purpose="exhaustive")
        self.assertEqual((top["profile"], top["model"], top["effort"]), ("review", "ts-3-prime", "xhigh"))
        lower = self.refusal(root, "review", "codex", variant_id="core", purpose="exhaustive")
        self.assertEqual((lower["kind"], lower["reason"]), ("review-purpose", "below-top-rank"))
        change_policy(root, lambda document: drop_review_seat(document, "exhaustive", "pi"))
        missing = self.refusal(root, "review", "pi", purpose="exhaustive")
        self.assertEqual((missing["kind"], missing["reason"]), ("review-purpose", "no-review-seat"))

    def test_an_exhaustive_seat_may_be_the_authors_own_lab_and_model(self):
        """Claim: exhaustive selects its seat from the author's own lab and
        even its own model, and the review block answers that read for what
        it is, as for any purpose: a same-lab read does not clear, an
        independent one does; without an author it is unverified. Rejects an
        exhaustive selection refused for sharing the author's lab, or a read
        answered by the purpose that chose it rather than by who reads."""
        for author in ("nw-atlas-2#high", "nw-atlas-2#xhigh", "nw-swift-2#high"):
            with self.subTest(author=author):
                review = resolve(FIXTURE, "review", "claude", author=author, purpose="exhaustive")["review"]
                self.assertEqual((review["purpose"], review["independence"], review["clears"]),
                                 ("exhaustive", "ineligible", False))
                self.assertIn("same-family", review["qualifiers"])
        own = resolve(FIXTURE, "review", "claude", author="nw-atlas-2#xhigh", purpose="exhaustive")["review"]
        self.assertEqual((own["findings"], own["qualifiers"]), ("eligible", ["same-model", "same-family"]))
        unverified = resolve(FIXTURE, "review", "claude", purpose="exhaustive")["review"]
        self.assertEqual((unverified["author"], unverified["independence"], "clears" in unverified),
                         (None, "unverified", False))
        independent = resolve(FIXTURE, "review", "claude", author="ts-3-core#max", purpose="exhaustive")["review"]
        self.assertEqual((independent["independence"], independent["clears"]), ("eligible", True))
        self.assertNotIn("purpose_qualifiers", independent)
        self.assertEqual(self.refusal(FIXTURE, "review", "claude", author="ts-3-core#max", purpose="exhaustive",
                                      accept_ineligible=True)["kind"], "invalid-purpose")

    def test_assess_judges_a_read_with_findings_or_clearance_never_exhaustive(self):
        """Claim: assess refuses --purpose exhaustive in both schemas, saying
        exhaustive selects a reader, and the reader an exhaustive selection
        dispatches is assessed like any other read, agreeing with resolve:
        another lab's strong reader clears and the author's own lab finds.
        Rejects an assessment that answers for the purpose that chose the
        reader, or that disagrees with resolve about the same read."""
        for schema in (1, 2):
            with self.subTest(schema=schema):
                with self.assertRaises(RouteRefusal) as caught:
                    assess_review(FIXTURE, "nw-atlas-2#xhigh", ["nw-swift-2#high"], purpose="exhaustive",
                                  schema=schema)
                self.assertEqual(caught.exception.kind, "invalid-purpose")
                self.assertIn("exhaustive selects a reader", caught.exception.message)
                self.assertIn("--purpose findings or clearance", caught.exception.message)
        for author, clears in (("ts-3-core#max", True), ("nw-swift-2#high", False)):
            with self.subTest(author=author):
                chosen = resolve(FIXTURE, "review", "claude", author=author, purpose="exhaustive")
                reader = f"{chosen['model']}#{chosen['effort']}"
                answer = assess_review(FIXTURE, reader, [author])
                self.assertEqual((answer["clears"], answer["findings"], chosen["review"]["clears"]),
                                 (clears, "eligible", clears))
                self.assertNotIn("purpose_qualifiers", answer)

    def test_existing_purposes_answer_multi_author_diffs_as_before(self):
        """Claim: clearance and findings give the same answers for a
        multi-author diff whichever is asked. Rejects a purpose changing an
        answer it does not own, such as withholding clearance from a
        findings question."""
        for purpose in ("clearance", "findings"):
            with self.subTest(purpose=purpose):
                mixed = assess_review(FIXTURE, "ts-3-prime#xhigh", ["orbit-flash#max", "nw-atlas-2#high"],
                                      purpose=purpose)
                self.assertEqual((mixed["floor"], mixed["independence"], mixed["findings"], mixed["clears"],
                                  mixed["qualifiers"], mixed["debt_kind"]),
                                 (2, "eligible", "eligible", True, [], None))
                own = assess_review(FIXTURE, "nw-atlas-2#xhigh", ["nw-swift-2#high", "orbit-flash#max"],
                                    purpose=purpose)
                self.assertEqual((own["independence"], own["findings"], own["clears"], own["qualifiers"],
                                  own["debt_kind"]),
                                 ("ineligible", "eligible", False, ["same-family"], "ineligible-review"))


class ReviewResolutionTest(unittest.TestCase):
    def refusal(self, *args, **options):
        with self.assertRaises(RouteRefusal) as caught:
            resolve(FIXTURE, *args, **options)
        return caught.exception.payload()

    def test_an_author_moves_review_to_an_independent_seat_or_debt(self):
        """Claim: with --author, resolve review answers only a seat that
        clears that author: another lab's seat on the backend, or a
        record-debt refusal when the backend has none. Rejects the author's
        own lab reviewing its work."""
        answer = resolve(FIXTURE, "review", "claude", author="ts-3-core#max")
        self.assertEqual((answer["model"], answer["review"]["clears"]), ("claude-atlas-2", True))
        refusal = self.refusal("review", "codex", author="ts-3-core#max")
        self.assertEqual((refusal["kind"], refusal["reason"], refusal["recommendation"]),
                         ("review-independence", "no-eligible-route", "record-debt"))

    def test_findings_seat_a_same_family_reviewer_that_clearance_refuses(self):
        """Claim: --purpose findings may answer a same-family seat above the
        author, marked as not clearing, where --purpose clearance refuses.
        Rejects a findings read sold as clearance."""
        found = resolve(FIXTURE, "review", "claude", author="nw-swift-2#high", purpose="findings")
        self.assertEqual((found["model"], found["review"]["findings"], found["review"]["clears"]),
                         ("claude-atlas-2", "eligible", False))
        self.assertEqual(self.refusal("review", "claude", author="nw-swift-2#high")["reason"], "no-eligible-route")

    def test_accept_ineligible_returns_the_seat_with_a_debt_kind(self):
        """Claim: --accept-ineligible answers the strongest seat even when it
        cannot clear, carrying ineligible-review debt, and needs an author.
        Rejects silently dropping the debt, or accepting with nothing to
        judge."""
        answer = resolve(FIXTURE, "review", "claude", author="nw-atlas-2#high", accept_ineligible=True)
        self.assertEqual((answer["review"]["clears"], answer["review"]["debt_kind"],
                          answer["review"]["recommendation"]), (False, "ineligible-review", "record-debt"))
        self.assertEqual(self.refusal("review", "claude", accept_ineligible=True)["kind"], "invalid-author")

    def test_an_unknown_author_recommends_debt_and_author_is_review_only(self):
        """Claim: an author whose facts are unknown is refused with a debt
        recommendation, and --author outside review is refused. Rejects
        guessing a floor, or an author silently ignored."""
        unknown = self.refusal("review", "claude", author="nobody#high")
        self.assertEqual((unknown["reason"], unknown["recommendation"]), ("unknown-author", "record-debt"))
        self.assertEqual(self.refusal("implement", "claude", author="ts-3-core#max")["kind"], "invalid-author")
        self.assertEqual(self.refusal("review", "claude", purpose="findings")["kind"], "invalid-purpose")


class FrontierTest(unittest.TestCase):
    def test_the_frontier_is_the_strongest_independent_review_seat(self):
        """Claim: the frontier for an author is the highest-tier stable review
        seat that may review it, excluding its own lab's seats. Rejects a
        frontier that offers the author's own lab."""
        answer = frontier_review(FIXTURE, "ts-3-core#max")
        self.assertEqual(answer["frontier"]["seats"],
                         [{"backend": "claude", "effort": "xhigh", "model": "nw-atlas-2", "pool": "northwind-plan"}])

    def test_tied_seats_are_all_listed_and_other_profiles_never_raise_it(self):
        """Claim: every eligible review seat at the top tier is listed, and a
        seat of another profile at that tier is not, nor is an experimental
        review seat. Rejects a frontier that hides a tie, or one raised by a
        seat review cannot sell."""
        seats = frontier_review(FIXTURE, "orbit-flash#max")["frontier"]["seats"]
        self.assertEqual([(seat["backend"], seat["model"], seat["effort"]) for seat in seats],
                         [("claude", "nw-atlas-2", "xhigh"), ("codex", "ts-3-prime", "xhigh")])
        root = scratch(self)
        edit(root, stores.POLICY, '[[family_exception]]\nreviewer = "nw-sage-2"\nauthors = ["nw-atlas-2", "nw-swift-2"]\n'
             'why = "The fixture\'s largest Northwind model may clear its siblings."\nsince = "2030-01-03"\n\n', "")
        edit(root, stores.POLICY, '[[fallback]]\nprofile = "review"',
             '[[seat]]\nprofile = "review"\nvariant = "sage-trial"\nbackends = ["claude"]\n'
             'provider = "northwind-plan"\nmodel = "nw-sage-2"\neffort = "high"\nstability = "experimental"\n'
             'when = "A trial read."\nwhy = "Unmeasured."\nsince = "2030-01-03"\n\n[[fallback]]\nprofile = "review"')
        self.assertEqual(data_problems(root), [])
        self.assertEqual(frontier_review(root, "orbit-flash#max")["frontier"]["seats"], seats)

    def test_reads_stand_by_tier_and_eligibility_stays_in_the_assessment(self):
        """Claim: a read stands at, above or below the frontier tier by tier
        alone, so an ineligible read still has a standing and its assessment
        says why. Rejects standing that hides an ineligible read's tier."""
        reads = frontier_review(FIXTURE, "orbit-flash#max",
                                ["ts-3-prime#xhigh", "nw-atlas-2#high", "orbit-flash#low"])["reads"]
        self.assertEqual([(read["standing"], read["assessment"]["independence"]) for read in reads],
                         [("at", "eligible"), ("below", "eligible"), ("below", "ineligible")])

    def test_without_a_frontier_reads_are_unranked(self):
        """Claim: when no seat reaches the author's floor the status says so
        and every read is unranked. Rejects a floor guessed to make a
        frontier."""
        root = scratch(self)
        edit(root, stores.CATALOG, 'model = "ts-3-prime"\neffort = "max"\nrank = 3\nfloor = 3',
             'model = "ts-3-prime"\neffort = "max"\nrank = 3\nfloor = 4')
        answer = frontier_review(root, "ts-3-prime#max", ["nw-atlas-2#xhigh"])
        self.assertEqual((answer["status"], answer["frontier"], answer["reads"][0]["standing"]),
                         ("no-eligible-seat", None, "unranked"))


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
