"""The roster's prices export as a tapes-price-table/2 file carrying every
term the roster records: a long-context surcharge as a long-context term for
API per-token billing only, time-of-day prices as UTC windows, and a dated
price change as one row per price with its validity window."""

import datetime
import pathlib
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tests"))
from price_export import price_export, price_problems, readable_table, tapes_table  # noqa: E402
from test_price_export import FixtureRoster  # noqa: E402

# The keys tapes-price-table/2 accepts; tapes refuses any other.
MODEL_KEYS = {"id", "aliases", "effective", "source", "per_million", "effective_from", "effective_until",
              "long_context", "time_of_day"}
LONG_CONTEXT_KEYS = {"above_prompt_tokens", "from_prompt_tokens", "prompt_tokens", "billing", "per_million",
                     "multipliers"}
PRICE_KEYS = {"uncached_input", "cache_read", "cache_write_5m", "cache_write_1h", "output"}

SURCHARGED_MODELS = '''
[[model]]
id = "over-1"
family = "fixture"
aliases = ["vendor-over-1"]
api_price_per_million = { input = 0.1, cached_input = 0.01, cache_write = 0.125, cache_write_1h = 0.2, output = 0.5 }
api_price_read = "2026-10-01"
long_context_surcharge = { threshold_input_tokens = 100000, threshold_inclusive = false, input_multiplier = 5.0, cache_multiplier = 4.0, output_multiplier = 3.0 }

[[model]]
id = "reach-2"
family = "fixture"
api_price_per_million = { input = 2.0, cached_input = 0.5, output = 6.0 }
api_price_read = "2026-10-02"
long_context_surcharge = { threshold_input_tokens = 200000, threshold_inclusive = true, input_multiplier = 2.0, cache_multiplier = 2.0, output_multiplier = 1.5 }

[[model]]
id = "flat-3"
family = "fixture"
api_price_per_million = { input = 2.0, output = 6.0 }
api_price_read = "2026-10-03"
'''


OFF_PEAK_MODELS = '''
[[model]]
id = "peak-4"
family = "fixture"
api_price_per_million = { cache_hit_input = 0.006, cache_miss_input = 0.30, output = 1.2 }
api_price_read = "2026-10-04"
time_of_day_prices = [{ from = "04:00", until = "06:00", multiplier = 0.5 }, { from = "10:00", until = "01:00", multiplier = 0.25 }]
'''


DATED_MODELS = '''
[[model]]
id = "dated-5"
family = "fixture"
aliases = ["vendor-dated-5"]
api_price_per_million = { input = 0.75, cached_input = 0.075, output = 3.75 }
api_price_read = "2026-10-05"
long_context_surcharge = { threshold_input_tokens = 200000, threshold_inclusive = false, input_multiplier = 2.0, cache_multiplier = 2.0, output_multiplier = 1.5 }
api_price_changes = [{ from = "2027-01-01", per_million = { input = 1.5, cached_input = 0.15, output = 7.5 } }, { from = "2027-07-01", per_million = { input = 3.0, cached_input = 0.3, output = 15.0 } }]
'''


def written_table(models: str) -> dict:
    with FixtureRoster(models) as root:
        return tomllib.loads(tapes_table(price_export(root)))


def assert_tapes_shape(case: unittest.TestCase, table: dict) -> None:
    """Every model uses only keys tapes-price-table/2 accepts."""
    case.assertEqual(table["schema"], "tapes-price-table/2")
    for model in table["models"]:
        case.assertLessEqual(set(model), MODEL_KEYS, model["id"])
        case.assertLessEqual(set(model["per_million"]), PRICE_KEYS, model["id"])
        if "long_context" in model:
            case.assertLessEqual(set(model["long_context"]), LONG_CONTEXT_KEYS, model["id"])
        for window in model.get("time_of_day", []):
            case.assertLessEqual({"from", "until", "per_million"}, set(window), model["id"])
            case.assertLessEqual(set(window), {"from", "until", "per_million", "days"}, model["id"])


class LongContextTermTest(unittest.TestCase):
    def test_a_surcharged_row_exports_its_prices_and_a_long_context_term(self):
        """Claim: a row with a long_context_surcharge is exported with its
        short-prompt prices and a long-context term counting the whole prompt
        (uncached input, cache reads and cache writes), scaling input by the
        input multiplier, cache reads and both cache-write TTLs by the cache
        multiplier and output by the output multiplier. Rejects a surcharged
        row exported with no price, which leaves its sessions unestimated, and
        one whose short-prompt rates reach tapes with no term, which prices a
        request over the threshold as complete at a fraction of its cost."""
        table = {model["id"]: model for model in written_table(SURCHARGED_MODELS)["models"]}
        over = table["over-1"]
        self.assertEqual(over["aliases"], ["vendor-over-1"])
        self.assertEqual(over["per_million"], {"uncached_input": 0.1, "cache_read": 0.01, "cache_write_5m": 0.125,
                                               "cache_write_1h": 0.2, "output": 0.5})
        self.assertEqual(over["long_context"]["prompt_tokens"], ["uncached_input", "cache_read", "cache_write"])
        self.assertEqual(over["long_context"]["multipliers"], {"uncached_input": 5.0, "cache_read": 4.0,
                                                               "cache_write_5m": 4.0, "cache_write_1h": 4.0,
                                                               "output": 3.0})
        self.assertNotIn("long_context", table["flat-3"])

    def test_the_threshold_keeps_the_vendors_boundary(self):
        """Claim: a surcharge a prompt pays once it is over the threshold is
        exported as above_prompt_tokens, and one it pays once the prompt
        reaches the threshold as from_prompt_tokens; a term scales only the
        categories its row prices. Rejects a prompt of exactly the threshold
        priced on the wrong side of it."""
        table = {model["id"]: model for model in written_table(SURCHARGED_MODELS)["models"]}
        self.assertEqual(table["over-1"]["long_context"]["above_prompt_tokens"], 100000)
        self.assertNotIn("from_prompt_tokens", table["over-1"]["long_context"])
        self.assertEqual(table["reach-2"]["long_context"]["from_prompt_tokens"], 200000)
        self.assertNotIn("above_prompt_tokens", table["reach-2"]["long_context"])
        self.assertEqual(table["reach-2"]["long_context"]["multipliers"],
                         {"uncached_input": 2.0, "cache_read": 2.0, "output": 1.5})

    def test_a_surcharge_applies_to_api_billing_only(self):
        """Claim: every long-context term names API per-token billing and no
        other, and the table's header says a subscription pays no surcharge.
        Rejects a term that would charge a Claude Code or Codex subscription
        session the surcharge."""
        with FixtureRoster(SURCHARGED_MODELS) as root:
            text = tapes_table(price_export(root))
        for model in tomllib.loads(text)["models"]:
            if "long_context" in model:
                with self.subTest(model=model["id"]):
                    self.assertEqual(model["long_context"]["billing"], ["api"])
        self.assertIn("a subscription plan pays no surcharge", " ".join(
            line.lstrip("# ") for line in text.splitlines() if line.startswith("#")))

    def test_the_table_takes_only_keys_tapes_accepts(self):
        """Claim: the written table is tapes-price-table/2 and every model and
        term uses only keys that format defines. Rejects a version 1 schema
        carrying version 2 terms, or a roster key in the output, either of
        which tapes refuses."""
        assert_tapes_shape(self, written_table(SURCHARGED_MODELS))

    def test_lint_refuses_a_surcharge_without_its_boundary(self):
        """Claim: a surcharge must say whether a prompt of exactly the
        threshold pays it. Rejects a surcharge exported on a guessed side."""
        for body in ('', 'threshold_inclusive = "yes", '):
            with self.subTest(body=body):
                models = tomllib.loads(
                    '[[model]]\nid = "x"\napi_price_per_million = { input = 1.0 }\napi_price_read = "2026-09-01"\n'
                    f'long_context_surcharge = {{ threshold_input_tokens = 1000, {body}input_multiplier = 2.0, '
                    'cache_multiplier = 2.0, output_multiplier = 2.0 }\n')["model"]
                self.assertTrue(any("threshold_inclusive must be true" in problem
                                    for problem in price_problems(models)), price_problems(models))

    def test_the_readable_table_names_each_term(self):
        """Claim: the bare `prices` table shows a surcharged row's prices and
        its term. Rejects a reader's table that hides the surcharge."""
        with FixtureRoster(SURCHARGED_MODELS) as root:
            text = readable_table(price_export(root))
        row = next(line for line in text.splitlines() if line.startswith("over-1\t"))
        self.assertIn("\t0.1\t", row)
        self.assertIn("above 100,000 prompt tokens, api billing: 5x uncached_input", row)


class TimeOfDayTest(unittest.TestCase):
    def test_time_of_day_prices_export_as_scaled_utc_windows(self):
        """Claim: each time_of_day_prices window is exported with its UTC
        bounds as written, one past midnight included, pricing every
        category the row prices at the row's price times its multiplier.
        Rejects a window that prices only some categories, which tapes would
        leave unpriced inside it, and one exported at the peak price."""
        table = written_table(OFF_PEAK_MODELS)
        assert_tapes_shape(self, table)
        model = table["models"][0]
        self.assertEqual(model["per_million"], {"uncached_input": 0.3, "cache_read": 0.006, "output": 1.2})
        self.assertEqual(model["time_of_day"], [
            {"from": "04:00", "until": "06:00",
             "per_million": {"uncached_input": 0.15, "cache_read": 0.003, "output": 0.6}},
            {"from": "10:00", "until": "01:00",
             "per_million": {"uncached_input": 0.075, "cache_read": 0.0015, "output": 0.3}},
        ])

    def test_lint_refuses_a_window_the_export_cannot_describe(self):
        """Claim: a window needs HH:MM UTC bounds that differ, a multiplier
        of at least zero, no overlap with another window of the row, and a
        priced row. Rejects a table tapes would refuse for overlapping or
        malformed windows."""
        cases = {
            '[{ from = "4:00", until = "06:00", multiplier = 0.5 }]': "must be UTC times written HH:MM",
            '[{ from = "24:00", until = "06:00", multiplier = 0.5 }]': "must be UTC times written HH:MM",
            '[{ from = "06:00", until = "06:00", multiplier = 0.5 }]': "must not start where it ends",
            '[{ from = "04:00", until = "06:00", multiplier = -0.5 }]': "multiplier must be a finite number",
            '[{ from = "22:00", until = "02:00", multiplier = 0.5 }, { from = "01:00", until = "03:00", multiplier = 0.5 }]':
                "windows overlap",
            '{ from = "04:00", until = "06:00", multiplier = 0.5 }': "must be a list of tables",
        }
        for body, expected in cases.items():
            with self.subTest(expected=expected):
                models = tomllib.loads('[[model]]\nid = "x"\napi_price_per_million = { input = 1.0 }\n'
                                       f'api_price_read = "2026-09-01"\ntime_of_day_prices = {body}\n')["model"]
                problems = price_problems(models)
                self.assertTrue(any(expected in problem for problem in problems), problems)
        unpriced = tomllib.loads('[[model]]\nid = "x"\n'
                                 'time_of_day_prices = [{ from = "04:00", until = "06:00", multiplier = 0.5 }]\n')
        self.assertTrue(price_problems(unpriced["model"]))


class PriceChangeTest(unittest.TestCase):
    def test_a_dated_change_exports_one_row_per_price(self):
        """Claim: a row with api_price_changes exports one model per price
        under the same id and aliases, the first in effect until the first
        change, each change from its date until the next, the last open,
        and each carrying the row's terms at its own rates. Rejects the
        current price applied past the vendor's change date, and a later
        price applied before it."""
        table = written_table(DATED_MODELS)
        assert_tapes_shape(self, table)
        rows = table["models"]
        self.assertEqual([row["id"] for row in rows], ["dated-5"] * 3)
        self.assertEqual([row["aliases"] for row in rows], [["vendor-dated-5"]] * 3)
        self.assertEqual([(row.get("effective_from"), row.get("effective_until")) for row in rows], [
            (None, datetime.date(2027, 1, 1)),
            (datetime.date(2027, 1, 1), datetime.date(2027, 7, 1)),
            (datetime.date(2027, 7, 1), None),
        ])
        self.assertEqual([row["per_million"]["uncached_input"] for row in rows], [0.75, 1.5, 3.0])
        self.assertEqual(rows[1]["per_million"], {"uncached_input": 1.5, "cache_read": 0.15, "output": 7.5})
        self.assertEqual([row["long_context"]["multipliers"]["output"] for row in rows], [1.5] * 3)
        self.assertIn("api_price_changes from 2027-01-01", rows[1]["source"])

    def test_lint_refuses_a_change_the_export_cannot_place(self):
        """Claim: a change needs a date after the read date and after the
        change before it, and prices for exactly the keys the row prices.
        Rejects validity windows tapes would refuse as meeting, and a change
        that silently drops a category."""
        cases = {
            '[{ from = "2026-08-01", per_million = { input = 2.0 } }]': "must come after the read date",
            '[{ from = "2027-02-01", per_million = { input = 2.0 } }, { from = "2027-01-01", per_million = { input = 3.0 } }]':
                "must come after the read date and the change before it",
            '[{ from = "2027-1-1", per_million = { input = 2.0 } }]': "must be a YYYY-MM-DD date",
            '[{ from = "2027-01-01", per_million = { output = 2.0 } }]': "must price the keys",
            '[{ from = "2027-01-01", per_million = { input = -2.0 } }]': "finite numbers of at least zero",
            '{ from = "2027-01-01", per_million = { input = 2.0 } }': "must be a list of tables",
        }
        for body, expected in cases.items():
            with self.subTest(expected=expected):
                models = tomllib.loads('[[model]]\nid = "x"\napi_price_per_million = { input = 1.0 }\n'
                                       f'api_price_read = "2026-09-01"\napi_price_changes = {body}\n')["model"]
                problems = price_problems(models)
                self.assertTrue(any(expected in problem for problem in problems), problems)
        unpriced = tomllib.loads('[[model]]\nid = "x"\n'
                                 'api_price_changes = [{ from = "2027-01-01", per_million = { input = 2.0 } }]\n')
        self.assertTrue(price_problems(unpriced["model"]))


class RosterTermsTest(unittest.TestCase):
    def roster(self) -> tuple[dict, dict]:
        models = {model["id"]: model for model in tomllib.loads(
            (ROOT / "routing" / "models.toml").read_text())["model"]}
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "prices.toml"
            result = subprocess.run([ROOT / "bin/agent-routing", "prices", "--format", "tapes", "--output", output],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            table = tomllib.loads(output.read_text())
        assert_tapes_shape(self, table)
        rows: dict[str, list[dict]] = {}
        for row in table["models"]:
            rows.setdefault(row["id"], []).append(row)
        return models, rows

    def test_every_roster_surcharge_is_exported_as_an_api_only_term(self):
        """Claim: every roster row with a long_context_surcharge (Haiku 5.5,
        Grok 4.6, the GPT-6 and GPT-5.6 families) is exported priced, with a
        long-context term for API billing only, Grok's from its 200k
        threshold and the others above theirs. Rejects a surcharged row left
        unpriced, and a Codex or Claude subscription session charged the
        surcharge."""
        models, rows = self.roster()
        surcharged = [model_id for model_id, model in models.items() if "long_context_surcharge" in model]
        self.assertLessEqual({"haiku-5.5", "grok-4.6", "gpt-6-astra", "gpt-6-luna", "gpt-6-sol", "gpt-6.1-sol",
                              "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}, set(surcharged))
        for model_id in surcharged:
            with self.subTest(model=model_id):
                for row in rows[model_id]:
                    self.assertTrue(row["per_million"])
                    self.assertEqual(row["long_context"]["billing"], ["api"])
        self.assertEqual(rows["grok-4.6"][0]["long_context"]["from_prompt_tokens"], 200000)
        self.assertEqual(rows["haiku-5.5"][0]["long_context"]["above_prompt_tokens"], 100000)
        self.assertEqual(rows["gpt-6-luna"][0]["long_context"]["above_prompt_tokens"], 272000)


    def test_gemini_flash_doubles_on_its_published_date(self):
        """Claim: Gemini 3.8 Flash exports its introductory price until
        2027-01-01 and the doubled price from then. Rejects a 2027 request
        priced at the introductory rate."""
        _, rows = self.roster()
        first, second = rows["gemini-3.8-flash"]
        self.assertEqual(first["effective_until"], datetime.date(2027, 1, 1))
        self.assertNotIn("effective_from", first)
        self.assertEqual(second["effective_from"], datetime.date(2027, 1, 1))
        self.assertEqual(second["per_million"], {category: 2 * price for category, price in first["per_million"].items()})


if __name__ == "__main__":
    unittest.main()
