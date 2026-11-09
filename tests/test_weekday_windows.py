"""A time-of-day window may name the UTC days of the week it opens on, and
the export carries them as tapes-price-table/2 `days`, so a weekday peak can
price off-peak on weekends."""

import pathlib
import sys
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tests"))
from price_export import price_export, price_problems, readable_table  # noqa: E402
from test_price_export import FixtureRoster  # noqa: E402
from test_price_table_v2 import assert_tapes_shape, written_table  # noqa: E402

WEEKDAY_MODELS = '''
[[model]]
id = "weekday-6"
family = "fixture"
api_price_per_million = { input = 1.0, output = 4.0 }
api_price_read = "2026-10-06"
time_of_day_prices = [{ from = "22:00", until = "02:00", multiplier = 0.5, days = ["fri"] }, { from = "01:00", until = "03:00", multiplier = 0.25, days = ["fri", "sun"] }, { from = "12:00", until = "13:00", multiplier = 0.75 }]
'''


class WeekdayExportTest(unittest.TestCase):
    def test_a_window_exports_the_days_it_opens_on(self):
        """Claim: a time_of_day_prices window that names days is exported as
        a tapes window carrying the same days, in the order written, and one
        that names none is exported without days, so it opens every day.
        Rejects a window exported without its days, which tapes would hold on
        every day of the week."""
        table = written_table(WEEKDAY_MODELS)
        assert_tapes_shape(self, table)
        model, = table["models"]
        self.assertEqual([(window["from"], window["until"], window.get("days")) for window in model["time_of_day"]],
                         [("22:00", "02:00", ["fri"]), ("01:00", "03:00", ["fri", "sun"]), ("12:00", "13:00", None)])
        self.assertEqual(model["time_of_day"][1]["per_million"], {"uncached_input": 0.25, "output": 1.0})

    def test_the_readable_table_names_a_windows_days(self):
        """Claim: the readable table names the days a window opens on.
        Rejects a weekday-only window shown as if it held every day."""
        with FixtureRoster(WEEKDAY_MODELS) as root:
            text = readable_table(price_export(root))
        self.assertIn("22:00-02:00 UTC fri: uncached_input 0.5, output 2", text)
        self.assertIn("12:00-13:00 UTC: uncached_input 0.75, output 3", text)


class WeekdayLintTest(unittest.TestCase):
    def problems(self, windows: str) -> list[str]:
        models = tomllib.loads('[[model]]\nid = "x"\napi_price_per_million = { input = 1.0 }\n'
                               f'api_price_read = "2026-09-01"\ntime_of_day_prices = {windows}\n')["model"]
        return price_problems(models)

    def test_windows_on_different_days_do_not_overlap(self):
        """Claim: the overlap check covers a whole week, so windows sharing
        hours on different days are accepted, and a window past midnight
        overlaps the next day's window in the hours it holds into it.
        Rejects the DeepSeek weekend windows refused as overlapping, and a
        Friday-night window overlapping a Saturday-morning one let through."""
        self.assertEqual(self.problems('[{ from = "01:00", until = "04:00", multiplier = 0.5, days = ["sat", "sun"] }, '
                                       '{ from = "01:00", until = "04:00", multiplier = 1.0, days = ["mon"] }, '
                                       '{ from = "22:00", until = "02:00", multiplier = 0.5, days = ["thu"] }]'), [])
        self.assertIn("x: time_of_day_prices windows overlap",
                      self.problems('[{ from = "22:00", until = "02:00", multiplier = 0.5, days = ["fri"] }, '
                                    '{ from = "01:00", until = "03:00", multiplier = 0.5, days = ["sat"] }]'))
        self.assertIn("x: time_of_day_prices windows overlap",
                      self.problems('[{ from = "10:00", until = "01:00", multiplier = 0.5 }, '
                                    '{ from = "00:00", until = "02:00", multiplier = 0.5, days = ["sun"] }]'))

    def test_lint_refuses_days_tapes_would_refuse(self):
        """Claim: days must list at least one of mon..sun, each once.
        Rejects a table tapes refuses for an empty list, an unknown day name
        or a day named twice."""
        cases = {
            "[]": "days must list at least one day",
            '"sat"': "days must list at least one day",
            '["saturday"]': "days are written mon, tue, wed, thu, fri, sat, sun, not 'saturday'",
            '["Sat"]': "not 'Sat'",
            '["sat", "sun", "sat"]': "days name 'sat' twice",
        }
        for days, expected in cases.items():
            with self.subTest(days=days):
                problems = self.problems(f'[{{ from = "01:00", until = "04:00", multiplier = 0.5, days = {days} }}]')
                self.assertTrue(any(expected in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
