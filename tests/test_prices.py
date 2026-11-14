"""API list prices over the fixture data: dated prices, time-of-day windows, surcharges and their validation."""

import tomllib
import unittest

from fixture import FIXTURE, edit, scratch

import price_export
import stores
from routing_profiles import data_problems

PRIME_WINDOW = ('[[price_window]]\nmodel = "ts-3-prime"\nfrom = "13:00"\nuntil = "17:00"\nmultiplier = 2.0\n'
                'days = ["mon", "tue", "wed", "thu", "fri"]\n')


def exported(root):
    return {(row["id"], row["effective_from"]): row for row in price_export.price_export(root)["models"]}


class DatedPriceTest(unittest.TestCase):
    def test_a_dated_price_splits_the_row_into_consecutive_periods(self):
        """Claim: a [[price]] row with `from` is a price change: the export
        carries one model per period, the first until the change and the
        change from its date on, each at its own rates and each keeping the
        row's long-context term. Rejects a change that overwrites the price it
        follows, or a period that loses its surcharge."""
        root = scratch(self)
        edit(root, stores.CATALOG, '[[surcharge]]\nmodel = "nw-swift-2"',
             '[[price]]\nmodel = "nw-swift-2"\nread = "2030-01-02"\nfrom = "2030-06-01"\ninput = 2.0\n'
             'cached_input = 0.2\ncache_write = 2.5\ncache_write_1h = 4.0\noutput = 10.0\n\n'
             '[[surcharge]]\nmodel = "nw-swift-2"')
        self.assertEqual(data_problems(root), [])
        rows = exported(root)
        before, after = rows[("nw-swift-2", None)], rows[("nw-swift-2", "2030-06-01")]
        self.assertEqual((before["effective_until"], after["effective_until"]), ("2030-06-01", None))
        self.assertEqual((before["per_million"]["uncached_input"], after["per_million"]["uncached_input"]),
                         (1.0, 2.0))
        self.assertEqual(after["long_context"]["above_prompt_tokens"], 100000)

    def test_a_price_change_must_follow_the_read_date_and_price_the_same_keys(self):
        """Claim: a change dated on or before the price it follows, or one
        pricing other categories, is refused by name. Rejects a period that
        runs backwards or silently drops a category."""
        root = scratch(self)
        edit(root, stores.CATALOG, '[[price_window]]\nmodel = "ts-3-prime"',
             '[[price]]\nmodel = "ts-3-prime"\nread = "2030-01-02"\nfrom = "2030-01-02"\ninput = 3.0\n'
             'output = 15.0\n\n[[price_window]]\nmodel = "ts-3-prime"')
        problems = data_problems(root)
        self.assertIn("ts-3-prime: api_price_changes from 2030-01-02 must come after the read date and the change "
                      "before it", problems)
        self.assertIn("ts-3-prime: api_price_changes per_million must price the keys api_price_per_million prices",
                      problems)


class WindowTest(unittest.TestCase):
    def test_weekday_and_cross_midnight_windows_export_scaled_prices(self):
        """Claim: each time-of-day window exports as a tapes window at the
        row's prices times its multiplier, carrying the days it names or none
        when it opens every day, including a window that runs past midnight.
        Rejects an export that drops a window, which prices peak hours at the
        off-peak rate."""
        root = scratch(self)
        edit(root, stores.CATALOG, PRIME_WINDOW,
             PRIME_WINDOW + '\n[[price_window]]\nmodel = "ts-3-prime"\nfrom = "22:00"\nuntil = "02:00"\n'
             'multiplier = 0.5\n')
        windows = exported(root)[("ts-3-prime", None)]["time_of_day"]
        self.assertEqual(windows, [
            {"from": "13:00", "until": "17:00", "per_million": {"uncached_input": 4.0, "cache_read": 0.4,
                                                               "output": 24.0},
             "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"from": "22:00", "until": "02:00", "per_million": {"uncached_input": 1.0, "cache_read": 0.1,
                                                               "output": 6.0}}])
        table = tomllib.loads(price_export.tapes_table(price_export.price_export(root)))
        prime = next(row for row in table["models"] if row["id"] == "ts-3-prime")
        self.assertEqual([window["from"] for window in prime["time_of_day"]], ["13:00", "22:00"])

    def test_overlap_is_checked_across_the_week_and_past_midnight(self):
        """Claim: windows sharing hours on different days do not overlap, a
        window running past midnight overlaps the next day's early window, and
        an overlap is refused by name. Rejects an overlap check confined to
        one day, which prices one minute twice."""
        root = scratch(self)
        edit(root, stores.CATALOG, PRIME_WINDOW,
             PRIME_WINDOW + '\n[[price_window]]\nmodel = "ts-3-prime"\nfrom = "13:00"\nuntil = "17:00"\n'
             'multiplier = 0.5\ndays = ["sat"]\n\n[[price_window]]\nmodel = "ts-3-prime"\nfrom = "23:00"\n'
             'until = "01:00"\nmultiplier = 0.5\ndays = ["sat"]\n')
        self.assertEqual(data_problems(root), [])
        edit(root, stores.CATALOG, 'until = "01:00"\nmultiplier = 0.5\ndays = ["sat"]\n',
             'until = "01:00"\nmultiplier = 0.5\ndays = ["sat"]\n\n[[price_window]]\nmodel = "ts-3-prime"\n'
             'from = "00:30"\nuntil = "02:00"\nmultiplier = 0.5\ndays = ["sun"]\n')
        self.assertIn("ts-3-prime: time_of_day_prices windows overlap", data_problems(root))

    def test_days_and_bounds_tapes_would_refuse_are_refused(self):
        """Claim: a window that starts where it ends, names an unknown day or
        a day twice, or has a negative multiplier is refused. Rejects a table
        tapes would refuse."""
        root = scratch(self)
        edit(root, stores.CATALOG, 'until = "17:00"\nmultiplier = 2.0\ndays = ["mon", "tue", "wed", "thu", "fri"]',
             'until = "17:00"\nmultiplier = -1.0\ndays = ["mon"]')
        self.assertIn("ts-3-prime: time_of_day_prices multiplier must be a finite number of at least zero",
                      data_problems(root))
        edit(root, stores.CATALOG, 'days = ["mon"]', 'days = ["mon", "someday"]')
        self.assertIn("data/catalog.toml [[price_window]] model=ts-3-prime from=13:00: days are written mon, tue, "
                      "wed, thu, fri, sat, sun", data_problems(root))
        edit(root, stores.CATALOG, 'days = ["mon", "someday"]', 'days = ["mon", "mon"]')
        self.assertIn("data/catalog.toml [[price_window]] model=ts-3-prime from=13:00: days must be a list of "
                      "distinct nonblank strings, not ['mon', 'mon']", data_problems(root))
        edit(root, stores.CATALOG, 'from = "13:00"\nuntil = "17:00"\nmultiplier = -1.0\ndays = ["mon", "mon"]',
             'from = "13:00"\nuntil = "13:00"\nmultiplier = 2.0')
        self.assertIn("ts-3-prime: a time_of_day_prices window must not start where it ends", data_problems(root))


class SurchargeTest(unittest.TestCase):
    def test_a_surcharge_term_scales_every_priced_category_on_api_billing(self):
        """Claim: a long-context term counts the whole prompt, names API
        billing only, keeps the vendor's boundary (above for an exclusive
        threshold, from for an inclusive one) and scales input by the input
        multiplier, cache reads and both cache writes by the cache multiplier
        and output by the output multiplier. Rejects a term that leaves a
        category at its short-prompt rate or charges a subscription."""
        root = scratch(self)
        edit(root, stores.CATALOG, "input_multiplier = 5.0\ncache_multiplier = 5.0\noutput_multiplier = 5.0",
             "input_multiplier = 2.0\ncache_multiplier = 3.0\noutput_multiplier = 4.0")
        term = exported(root)[("nw-swift-2", None)]["long_context"]
        self.assertEqual(term, {"above_prompt_tokens": 100000,
                                "prompt_tokens": ["uncached_input", "cache_read", "cache_write"],
                                "billing": ["api"],
                                "multipliers": {"uncached_input": 2.0, "cache_read": 3.0, "cache_write_5m": 3.0,
                                                "cache_write_1h": 3.0, "output": 4.0}})
        edit(root, stores.CATALOG, "threshold_inclusive = false", "threshold_inclusive = true")
        term = exported(root)[("nw-swift-2", None)]["long_context"]
        self.assertEqual((term.get("from_prompt_tokens"), "above_prompt_tokens" in term), (100000, False))

    def test_a_surcharge_multiplier_below_one_is_refused(self):
        """Claim: surcharge multipliers are at least one. Rejects a
        'surcharge' that discounts a long prompt."""
        root = scratch(self)
        edit(root, stores.CATALOG, "cache_multiplier = 5.0", "cache_multiplier = 0.5")
        self.assertIn("nw-swift-2: long_context_surcharge.cache_multiplier must be a finite number of at least one",
                      data_problems(root))


class RateTest(unittest.TestCase):
    def test_negative_doubled_and_unread_prices_are_refused(self):
        """Claim: a negative or non-finite price, and two keys pricing one
        category, are refused by name. Rejects a table tapes would read as a
        credit or price twice."""
        root = scratch(self)
        edit(root, stores.CATALOG, "input = 0.2\ncached_input = 0.02\noutput = 1.2",
             "input = -0.2\ncache_miss_input = 0.3\ncached_input = 0.02\noutput = 1.2")
        problems = data_problems(root)
        self.assertIn("ts-3-core: api_price_per_million.input must be a finite number of at least zero", problems)
        self.assertIn("ts-3-core: 'input' and 'cache_miss_input' price the same category", problems)
        edit(root, stores.CATALOG, "input = -0.2\ncache_miss_input = 0.3", "input = 0.2")
        edit(root, stores.CATALOG, "cached_input = 0.02\noutput = 1.2", "cached_input = 0.02\noutput = nan")
        self.assertIn("data/catalog.toml [[price]] model=ts-3-core: output must be a finite number, not nan",
                      data_problems(root))

    def test_cache_writes_and_credits_follow_the_family_ratios(self):
        """Claim: a Northwind row's cache writes are its family's multiples of
        input, and a Tessel row's credits are its family's credits per API
        dollar. Rejects a write or credit rate left behind when a price moved."""
        root = scratch(self)
        edit(root, stores.CATALOG, "input = 1.0\ncached_input = 0.1\ncache_write = 1.25\ncache_write_1h = 2.0",
             "input = 1.0\ncached_input = 0.1\ncache_write = 1.25\ncache_write_1h = 3.0")
        edit(root, stores.CATALOG, "[[credit]]\nmodel = \"ts-3-prime\"\ninput = 50.0",
             "[[credit]]\nmodel = \"ts-3-prime\"\ninput = 40.0")
        problems = " ".join(data_problems(root))
        self.assertIn("nw-swift-2", problems)
        self.assertIn("cache_write_1h", problems)
        self.assertIn("data/catalog.toml [[credit]] model=ts-3-prime: input credits must be 25", problems)

    def test_the_fixture_prices_are_valid(self):
        """Claim: the fixture's prices pass, so each refusal above is the
        edit's. Rejects a test that passes on a fixture already refused."""
        self.assertEqual(price_export.price_problems(stores.load(FIXTURE).models), [])


if __name__ == "__main__":
    unittest.main()
