"""Admission against caller-supplied usage snapshots, over the fixture data."""

import unittest

from fixture import FIXTURE

from quota_routing import pool_window
from routing_profiles import RouteRefusal, resolve

NOW = 2_000_000_000


def window(remaining, *, resets_at=NOW + 3600):
    return {"used_percentage": 100 - remaining, "remaining_percentage": remaining, "resets_at": resets_at}


def usage(*, northwind=50, northwind_week=50, tessel=50, updated_at=NOW):
    return {"claude": {"state": "fresh", "updated_at": updated_at, "five_hour": window(northwind),
                       "seven_day": window(northwind_week)},
            "codex": {"state": "fresh", "updated_at": updated_at, "seven_day": window(tessel)}}


class PoolWindowTest(unittest.TestCase):
    def test_stale_inconsistent_and_expired_snapshots_are_unknown(self):
        """Claim: a snapshot older than the policy's max_age_seconds, one
        whose used and remaining shares do not sum to 100, one whose window
        has already reset, and one not marked fresh each leave the pool
        unknown. Rejects admitting on a reading that no longer describes the
        window."""
        cases = {"stale": usage(updated_at=NOW - 301),
                 "inconsistent": {**usage(), "claude": {**usage()["claude"],
                                                        "five_hour": {**window(50), "used_percentage": 40}}},
                 "expired": {**usage(), "claude": {**usage()["claude"],
                                                   "five_hour": window(50, resets_at=NOW)}},
                 "not fresh": {**usage(), "claude": {**usage()["claude"], "state": "cached"}}}
        self.assertEqual(pool_window(FIXTURE, "northwind-plan", usage(updated_at=NOW - 300), NOW)["state"],
                         "available")
        for name, snapshot in cases.items():
            with self.subTest(name):
                self.assertEqual(pool_window(FIXTURE, "northwind-plan", snapshot, NOW)["state"], "unknown")

    def test_a_pool_is_measured_by_the_windows_its_plan_declares(self):
        """Claim: a pool missing a window its plan declares is unknown, one
        without a usage key is never measured, and a window the plan does not
        declare still blocks when reported exhausted. Rejects reading an
        absent window as room, or ignoring an exhausted one."""
        missing = {**usage(), "claude": {key: value for key, value in usage()["claude"].items()
                                         if key != "seven_day"}}
        self.assertEqual(pool_window(FIXTURE, "northwind-plan", missing, NOW)["state"], "unknown")
        self.assertEqual(pool_window(FIXTURE, "flat-pool", usage(), NOW)["state"], "unknown")
        undeclared = {**usage(), "codex": {**usage()["codex"], "five_hour": window(0)}}
        self.assertEqual(pool_window(FIXTURE, "tessel-plan", undeclared, NOW)["state"], "exhausted")

    def test_weekly_exhaustion_blocks_an_otherwise_healthy_window(self):
        """Claim: a pool is exhausted when any window it reports is at zero,
        the weekly one included. Rejects admitting on a healthy five-hour
        window while the week is spent."""
        self.assertEqual(pool_window(FIXTURE, "northwind-plan", usage(northwind=90, northwind_week=0), NOW)["state"],
                         "exhausted")


class AdmissionTest(unittest.TestCase):
    def test_an_unmeasured_pool_is_refused_before_dispatch(self):
        """Claim: resolve with a usage snapshot refuses a route whose pool is
        unknown, naming the pool. Rejects dispatching blind into a window the
        caller asked to have checked."""
        with self.assertRaises(RouteRefusal) as caught:
            resolve(FIXTURE, "implement", "pi", usage=usage(), now=NOW)
        payload = caught.exception.payload()
        self.assertEqual((payload["kind"], payload["provider"]), ("quota-unknown", "flat-pool"))

    def test_a_weekly_exhausted_pool_falls_back_and_records_the_skipped_route(self):
        """Claim: an exhausted pool moves to the policy's fallback and records
        the route it skipped with its quota. Rejects a fallback that hides
        what it rerouted from."""
        answer = resolve(FIXTURE, "implement", "claude", usage=usage(northwind_week=0), now=NOW)
        self.assertEqual((answer["backend"], answer["provider"]), ("codex", "tessel-plan"))
        skipped = answer["rerouted_from"]
        self.assertEqual((skipped["provider"], skipped["reason"], skipped["quota"]["state"]),
                         ("northwind-plan", "pool-exhausted", "exhausted"))

    def test_a_pinned_variant_never_falls_back(self):
        """Claim: a named variant on an exhausted pool is refused as
        pool-exhausted, marked pinned, rather than rerouted. Rejects swapping
        the seat a caller named for another."""
        with self.assertRaises(RouteRefusal) as caught:
            resolve(FIXTURE, "implement", "claude", variant_id="atlas-high", usage=usage(northwind=0), now=NOW)
        payload = caught.exception.payload()
        self.assertEqual((payload["kind"], payload["pinned"], len(payload["skipped_routes"])),
                         ("pool-exhausted", True, 1))

    def test_a_fallback_into_an_exhausted_pool_is_refused_with_both_skips(self):
        """Claim: when the fallback's pool is exhausted too, resolve refuses
        and lists both skipped routes. Rejects dispatching into the second
        exhausted window."""
        with self.assertRaises(RouteRefusal) as caught:
            resolve(FIXTURE, "implement", "claude", usage=usage(northwind=0, tessel=0), now=NOW)
        skipped = caught.exception.payload()["skipped_routes"]
        self.assertEqual([(route["provider"], route["reason"]) for route in skipped],
                         [("northwind-plan", "pool-exhausted"), ("tessel-plan", "pool-exhausted")])

    def test_a_fallback_confirmation_describes_the_returned_seat(self):
        """Claim: with a caller, a rerouted answer's confirmation compares the
        caller with the seat actually returned, on its pool, and quotes that
        seat's purpose. Rejects advice about the exhausted seat the caller
        will not get."""
        answer = resolve(FIXTURE, "implement", "claude", usage=usage(northwind=0), now=NOW,
                         caller="ts-3-core#low", caller_provider="tessel-plan")
        confirmation = answer["confirmation"]
        self.assertEqual((confirmation["selection"]["provider"], confirmation["selection"]["model"],
                          confirmation["rank_comparison"], confirmation["offer_to_user"]),
                         ("tessel-plan", "ts-3-core", "above", True))
        self.assertEqual(confirmation["benefit"], "Specified implementation on the Tessel window.")


if __name__ == "__main__":
    unittest.main()
