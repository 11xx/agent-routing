"""Resolving a profile and validating a directed selection, over the fixture data."""

import unittest

from fixture import FIXTURE, edit, scratch

from routing_profiles import RouteRefusal, data_problems, resolve, routes_view, seats_view, validate_selection
import stores

NOW = 2_000_000_000


def window(remaining):
    return {"used_percentage": 100 - remaining, "remaining_percentage": remaining, "resets_at": NOW + 3600}


def usage(*, northwind=50, tessel=50):
    return {"claude": {"state": "fresh", "updated_at": NOW, "five_hour": window(northwind),
                       "seven_day": window(northwind)},
            "codex": {"state": "fresh", "updated_at": NOW, "seven_day": window(tessel)}}


class ResolveTest(unittest.TestCase):
    def refusal(self, call, *args, **options) -> dict:
        with self.assertRaises(RouteRefusal) as caught:
            call(*args, **options)
        return caught.exception.payload()

    def test_each_backend_gets_its_own_seat(self):
        """Claim: a profile answers each backend with the seat bound to it,
        naming the backend's model string from the catalog's reach row. Rejects
        a resolver that answers every backend with the primary seat."""
        answers = {backend: resolve(FIXTURE, "implement", backend) for backend in ("codex", "pi", "claude")}
        self.assertEqual({backend: (answer["model"], answer["effort"], answer["provider"])
                          for backend, answer in answers.items()},
                         {"codex": ("ts-3-core", "max", "tessel-plan"),
                          "pi": ("orbit-flash-0101", "max", "flat-pool"),
                          "claude": ("claude-atlas-2", "medium", "northwind-plan")})
        self.assertEqual(answers["claude"]["profile"], "implement:atlas")

    def test_one_seat_row_serves_each_backend_it_names(self):
        """Claim: a route that several backends serve is one seat row naming
        them, so editing that row's effort changes the answer on every one of
        those backends and needs no other row. Rejects per-backend copies that
        must be kept in agreement by hand."""
        root = scratch(self)
        self.assertEqual({backend: resolve(root, "survey", backend)["effort"] for backend in ("codex", "pi")},
                         {"codex": "high", "pi": "high"})
        edit(root, stores.POLICY, 'model = "ts-3-core"\neffort = "high"\nstability = "stable"\n'
             'when = "Surveys from a Tessel or pi session."', 'model = "ts-3-core"\neffort = "max"\n'
             'stability = "stable"\nwhen = "Surveys from a Tessel or pi session."')
        edit(root, stores.POLICY, '[[seat_rank]]\nmodel = "ts-3-core"\neffort = "high"\npool = "tessel-plan"\nrank = 1\n\n', "")
        self.assertEqual(data_problems(root), [])
        self.assertEqual({backend: resolve(root, "survey", backend)["effort"] for backend in ("codex", "pi")},
                         {"codex": "max", "pi": "max"})

    def test_a_named_variant_wins_over_the_default(self):
        """Claim: --variant selects that seat. Rejects ignoring the caller's choice."""
        answer = resolve(FIXTURE, "implement", "claude", variant_id="atlas-high")
        self.assertEqual((answer["model"], answer["effort"]), ("claude-atlas-2", "high"))

    def test_a_backend_without_a_seat_is_refused(self):
        """Claim: a backend no seat of the profile serves is refused, not
        answered with another backend's seat."""
        refusal = self.refusal(resolve, FIXTURE, "implement", "opencode")
        self.assertIn("does not support backend 'opencode'", refusal["message"])

    def test_an_experimental_seat_needs_the_opt_in(self):
        """Claim: an experimental seat resolves only with --allow-experimental.
        Rejects routing to an unmeasured model by default."""
        refusal = self.refusal(resolve, FIXTURE, "implement", "pi", variant_id="trial")
        self.assertEqual((refusal["kind"], refusal["override"]), ("stability", "--allow-experimental"))
        answer = resolve(FIXTURE, "implement", "pi", variant_id="trial", allow_experimental=True)
        self.assertEqual(answer["model"], "orbit-trial")

    def test_an_exhausted_pool_falls_back_along_the_policy(self):
        """Claim: when the selected seat's pool is exhausted, resolve moves to
        the fallback the policy names for that profile and provider, recording
        what it rerouted from. Rejects dispatching into an exhausted window."""
        answer = resolve(FIXTURE, "implement", "claude", usage=usage(northwind=0), now=NOW)
        self.assertEqual((answer["backend"], answer["model"]), ("codex", "ts-3-core"))
        self.assertEqual(answer["rerouted_from"]["reason"], "pool-exhausted")
        self.assertEqual(resolve(FIXTURE, "implement", "claude", usage=usage(), now=NOW)["backend"], "claude")

    def test_seats_and_routes_list_every_binding(self):
        """Claim: the seats view lists every profile, variant and backend
        binding, and the routes view lists the prohibited tiers with their
        reason. Rejects a view that hides a seat or a ban."""
        seats = {(seat["profile"], seat["variant"], seat["backend"]) for seat in seats_view(FIXTURE)["seats"]}
        self.assertIn(("implement", "trial", "pi"), seats)
        self.assertIn(("review", None, "codex"), seats)
        banned = routes_view(FIXTURE)["prohibited"]
        self.assertIn({"model": "nw-atlas-2", "effort": "max",
                       "reason": "Fixture ban: the top tier buys nothing over xhigh."},
                      [{key: row[key] for key in ("model", "effort", "reason")} for row in banned])


class ValidateTest(unittest.TestCase):
    def refusal(self, *args, **options) -> dict:
        with self.assertRaises(RouteRefusal) as caught:
            validate_selection(FIXTURE, *args, "fixture reason", **options)
        return caught.exception.payload()

    def test_a_prohibited_tier_is_refused_by_name(self):
        """Claim: a prohibited tier is refused even when named directly.
        Rejects a ban that only steers defaults."""
        refusal = self.refusal("implement", "claude", "nw-atlas-2", "max", "northwind-plan")
        self.assertEqual(refusal["kind"], "prohibited")

    def test_a_superseded_model_names_its_successor(self):
        """Claim: a model with a status is refused with that status and its
        successor. Rejects selecting a superseded model, or refusing without
        saying what replaces it."""
        refusal = self.refusal("implement", "claude", "nw-atlas-1", "high", "northwind-plan")
        self.assertEqual((refusal["kind"], refusal["model_status"], refusal["successor"]),
                         ("model-role", "superseded", "nw-atlas-2"))
        self.assertEqual(refusal["message"], "model 'nw-atlas-1' is superseded; its successor is 'nw-atlas-2'")

    def test_a_fence_keeps_a_model_off_a_profile(self):
        """Claim: a policy fence refuses its model on its profile with the
        fence's reason, even with the experimental opt-in. Rejects a fence the
        opt-in waives."""
        refusal = self.refusal("review", "pi", "orbit-trial", "high", "flat-pool", allow_experimental=True)
        self.assertEqual(refusal["fence"], "A trial model is never the reviewer of record.")

    def test_a_pool_refuses_a_model_it_does_not_serve(self):
        """Claim: a pool refuses a model outside its serves list and names who
        pays for it, unless the caller allows cross-pool spend. Rejects
        spending one plan's allowance on another plan's model."""
        refusal = self.refusal("implement", "pi", "ts-3-prime", "high", "flat-pool")
        self.assertEqual((refusal["kind"], refusal["override"]), ("pool", "--allow-cross-pool"))

    def test_an_unreachable_model_is_refused(self):
        """Claim: a model the catalog does not reach through the backend and
        provider is refused. Rejects launching a model string the backend
        cannot run."""
        refusal = self.refusal("implement", "pi", "ts-3-prime", "high", "flat-pool", allow_cross_pool=True)
        self.assertEqual(refusal["kind"], "unsupported-model")

    def test_an_offer_above_the_callers_seat_quotes_the_seat(self):
        """Claim: a selection above the caller's own seat is an offer to the
        user whose benefit is the selected seat's `when`. Rejects an offer
        that does not say what the higher tier buys."""
        answer = validate_selection(FIXTURE, "implement", "claude", "nw-atlas-2", "high", "northwind-plan",
                                    "fixture reason", caller="nw-atlas-2#medium")
        confirmation = answer["confirmation"]
        self.assertTrue(confirmation["offer_to_user"])
        self.assertEqual(confirmation["benefit"], "Implementation that needs the head model's standing tier.")

    def test_the_benefit_is_the_selected_seats_own_when(self):
        """Claim: the benefit is the `when` of the seat being selected, the
        named profile's seat on that backend and provider, even where another
        profile's seat holds the same tier first. Rejects quoting whichever
        seat holds the tier first, which described review work with the
        implement seat's purpose."""
        resolved = resolve(FIXTURE, "review", "pi", caller="orbit-flash#low")
        validated = validate_selection(FIXTURE, "review", "pi", "orbit-flash", "max", "flat-pool", "fixture reason",
                                       caller="orbit-flash#low")
        self.assertEqual((resolved["confirmation"]["benefit"], validated["confirmation"]["benefit"]),
                         ("Review from pi.", "Review from pi."))

    def test_a_selection_no_seat_holds_has_no_benefit(self):
        """Claim: a directed selection that is no seat of its profile carries
        a null benefit. Rejects borrowing the purpose of a seat on another
        pool or profile, which describes work the selection is not for."""
        answer = validate_selection(FIXTURE, "extract", "pi", "ts-3-core", "low", "flat-pool", "fixture reason",
                                    allow_experimental=True, caller="orbit-flash#low")
        self.assertIsNone(answer["confirmation"]["benefit"])

    def test_a_seated_upgrade_is_a_stable_operator_escalation(self):
        """Claim: a selection the profile seats stably above its baseline, or
        that an escalation source seats, is stable and reported as an
        operator escalation upward from the profile's own route. Rejects an
        upgrade recorded as ordinary, or a borrowed seat refused."""
        for model, effort in (("nw-atlas-2", "high"), ("nw-sage-2", "high")):
            with self.subTest(model=model):
                answer = validate_selection(FIXTURE, "implement", "claude", model, effort, "northwind-plan",
                                            "fixture reason")
                self.assertEqual((answer["stability"], answer["selection_kind"], answer["direction"],
                                  answer["baseline"]),
                                 ("stable", "operator-escalation", "upgrade", "nw-atlas-2#medium"))
        named = validate_selection(FIXTURE, "implement", "claude", "nw-atlas-2", "medium", "northwind-plan",
                                   "fixture reason")
        self.assertEqual((named["selection_kind"], named["direction"]), ("operator-directed", "same"))

    def test_an_unseated_tuple_needs_an_opt_in_and_stays_experimental(self):
        """Claim: a tuple neither the profile nor an escalation source seats
        is refused with the seated efforts listed, and with
        --allow-experimental it is experimental with its direction against
        the baseline. Rejects promoting an unseated tier to stable."""
        refusal = self.refusal("implement", "codex", "ts-3-core", "low", "tessel-plan")
        self.assertEqual((refusal["kind"], refusal["override"]), ("stability", "--allow-experimental"))
        self.assertIn("seated efforts for 'ts-3-core' on 'implement'/'codex'/'tessel-plan': max", refusal["message"])
        answer = validate_selection(FIXTURE, "implement", "codex", "ts-3-core", "low", "tessel-plan",
                                    "fixture reason", allow_experimental=True)
        self.assertEqual((answer["stability"], answer["direction"]), ("experimental", "downgrade"))

    def test_operator_named_permits_explicit_only_but_keeps_bans_and_fences(self):
        """Claim: --operator-named admits an explicit-only or experimental
        tuple the operator named, recording that, and still refuses a
        prohibited tier and a fenced profile. Rejects a named tuple that
        waives a ban."""
        answer = validate_selection(FIXTURE, "implement", "claude", "nw-swift-2", "max", "northwind-plan",
                                    "fixture reason", operator_named=True)
        self.assertEqual((answer["operator_named"], answer["stability"]), (True, "experimental"))
        self.assertEqual(self.refusal("implement", "claude", "nw-atlas-2", "max", "northwind-plan",
                                      operator_named=True)["kind"], "prohibited")
        self.assertIn("fence", self.refusal("review", "pi", "orbit-trial", "high", "flat-pool", operator_named=True))

    def test_a_role_exception_seats_a_fenced_model_only_on_a_variant(self):
        """Claim: a variant with a nonblank role_exception may seat a model
        fenced off its profile, and resolve reports the exception; the same
        seat without the reason is refused by the validator. Rejects an
        exception that is silent, or a fence a bare seat walks through."""
        root = scratch(self)
        seat = ('[[seat]]\nprofile = "review"\nvariant = "trial-read"\nbackends = ["pi"]\nprovider = "flat-pool"\n'
                'model = "orbit-trial"\neffort = "high"\nstability = "experimental"\n{exception}'
                'when = "A trial read beside the reviewer of record."\nwhy = "Fixture trial."\nsince = "2030-01-03"\n\n')
        edit(root, stores.POLICY, '[[fallback]]\nprofile = "review"',
             seat.format(exception="") + '[[fallback]]\nprofile = "review"')
        self.assertTrue(any("cannot serve profile 'review'" in problem for problem in data_problems(root)))
        edit(root, stores.POLICY, 'stability = "experimental"\nwhen = "A trial read',
             'stability = "experimental"\nrole_exception = "A candidate reader, never the verdict."\nwhen = "A trial read')
        self.assertEqual(data_problems(root), [])
        answer = resolve(root, "review", "pi", variant_id="trial-read", allow_experimental=True)
        self.assertEqual(answer["role_exception"], "A candidate reader, never the verdict.")

    def test_an_effort_the_backend_cannot_express_is_refused(self):
        """Claim: an effort outside a backend's support for that model (here
        pi's effort_support row) is refused. Rejects a route the harness would
        silently clamp."""
        with self.assertRaises(RouteRefusal) as caught:
            validate_selection(FIXTURE, "implement", "pi", "ts-3-core", "medium", "tessel-plan", "fixture reason")
        self.assertIn("medium", caught.exception.payload()["message"])


class CallerTest(unittest.TestCase):
    def confirmation(self, profile, backend, caller, provider=None, **options):
        return resolve(FIXTURE, profile, backend, caller=caller, caller_provider=provider, **options)["confirmation"]

    def summary(self, *args, **options):
        answer = self.confirmation(*args, **options)
        return answer["offer_to_user"], answer["reasons"], answer["rank_comparison"], answer["pool_comparison"]

    def test_a_higher_rank_or_a_scarcer_pool_is_offered(self):
        """Claim: a selection ranked above the caller's seat in its pool, or
        drawn from a pool declared scarcer than the caller's, is an offer with
        its reason. Rejects spending more than the caller's seat unasked."""
        self.assertEqual(self.summary("implement", "claude", "nw-swift-2#high", variant_id="atlas-high"),
                         (True, ["above-caller-seat"], "above", "same"))
        self.assertEqual(self.summary("implement", "claude", "ts-3-core#low", "tessel-plan"),
                         (True, ["scarcer-pool"], "unranked", "scarcer"))

    def test_lower_seats_are_ordinary_and_unknown_comparisons_stay_unknown(self):
        """Claim: a lower rank in the same pool is a known ordinary move,
        while a less scarce pool, an unordered pool and an unranked caller
        tier compare as unknown. Rejects inventing a cross-pool tier cost."""
        self.assertEqual(self.summary("implement", "claude", "nw-atlas-2#high"), (False, [], "below", "same"))
        self.assertEqual(self.summary("implement", "codex", "nw-atlas-2#high"), (None, [], "unranked", "less-scarce"))
        self.assertEqual(self.summary("implement", "claude", "orbit-flash#low"), (None, [], "unranked", "unranked"))
        self.assertEqual(self.summary("implement", "claude", "nw-atlas-2#low"), (None, [], "unranked", "same"))

    def test_an_ambiguous_or_invalid_caller_is_refused(self):
        """Claim: a caller model several pools serve needs --caller-provider,
        a provider that does not serve it is refused, and a caller needs an
        effort. Rejects guessing the caller's pool."""
        cases = {("ts-3-core#max", None): "invalid-caller", ("nw-atlas-2#high", "tessel-plan"): "invalid-caller",
                 ("nw-atlas-2", None): "unknown-coordinate", (None, "tessel-plan"): "invalid-caller"}
        for (caller, provider), kind in cases.items():
            with self.subTest(caller=caller, provider=provider):
                with self.assertRaises(RouteRefusal) as caught:
                    resolve(FIXTURE, "implement", "claude", caller=caller, caller_provider=provider)
                self.assertEqual(caught.exception.payload()["kind"], kind)


if __name__ == "__main__":
    unittest.main()
