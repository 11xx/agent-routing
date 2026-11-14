"""Resolving a profile and validating a directed selection, over the fixture data."""

import unittest

from fixture import FIXTURE

from routing_profiles import RouteRefusal, resolve, routes_view, seats_view, validate_selection

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

    def test_an_offer_on_another_pool_quotes_the_seat_holding_the_tier(self):
        """Claim: when no seat holds the selected tier on the selection's own
        provider, the benefit is the `when` of a seat holding that tier on
        another. Rejects an offer that goes silent because the pool differs."""
        answer = validate_selection(FIXTURE, "extract", "pi", "ts-3-core", "low", "flat-pool", "fixture reason",
                                    allow_experimental=True, caller="orbit-flash#low")
        self.assertEqual(answer["confirmation"]["benefit"], "Fixed-shape calls on the Tessel window.")

    def test_an_effort_the_backend_cannot_express_is_refused(self):
        """Claim: an effort outside a backend's support for that model (here
        pi's effort_support row) is refused. Rejects a route the harness would
        silently clamp."""
        with self.assertRaises(RouteRefusal) as caught:
            validate_selection(FIXTURE, "implement", "pi", "ts-3-core", "medium", "tessel-plan", "fixture reason")
        self.assertIn("medium", caught.exception.payload()["message"])


if __name__ == "__main__":
    unittest.main()
