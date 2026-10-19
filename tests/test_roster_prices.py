"""Every roster price carries the date it was read, and a row whose list
price rises above a prompt-size threshold exports no price tapes would apply
unconditionally: tapes-price-table/1 prices a figure's categories at one rate
and has no term for a threshold, so a short-prompt rate exported there would
price a request over the threshold as complete at a fraction of its cost."""

import pathlib
import sys
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tests"))
from price_export import price_export, price_problems, readable_table, tapes_table  # noqa: E402
from test_price_export import FixtureRoster  # noqa: E402

SURCHARGED_MODELS = '''
[[model]]
id = "short-1"
family = "fixture"
aliases = ["vendor-short-1"]
api_price_per_million = { input = 0.1, cached_input = 0.01, cache_write = 0.125, cache_write_1h = 0.2, output = 0.5 }
api_price_read = "2026-10-01"
long_context_surcharge = { threshold_input_tokens = 100000, input_multiplier = 5.0, cache_multiplier = 5.0, output_multiplier = 5.0, applies = "the full request" }

[[model]]
id = "flat-2"
family = "fixture"
api_price_per_million = { input = 2.0, output = 6.0 }
api_price_read = "2026-10-01"
'''


def list_price(per_million: dict, tokens: dict) -> tuple[float, list[str]]:
    """A figure priced the way tapes prices one: each category with tokens at
    its row price, and a category with tokens but no price named missing."""
    amount, missing = 0.0, []
    for category, count in tokens.items():
        if not count:
            continue
        if category in per_million:
            amount += count * per_million[category] / 1_000_000
        else:
            missing.append(category)
    return amount, missing


class RosterPricesTest(unittest.TestCase):
    def test_a_price_without_a_read_date_is_refused_whatever_the_reason(self):
        """Claim: every priced row needs api_price_read; a stated reason in
        api_price_undated does not stand in for it. Rejects a lint that
        accepts the undated exemption and lets a priced row with no read date
        pass with no errors."""
        models = tomllib.loads('''
[[model]]
id = "x"
api_price_per_million = { input = 1.0 }
api_price_undated = "no read date known"
''')["model"]
        problems = price_problems(models)
        self.assertTrue(any("needs api_price_read" in problem for problem in problems), problems)
        self.assertTrue(any("api_price_undated is not accepted" in problem for problem in problems), problems)

    def test_a_surcharged_row_prices_no_request_over_its_threshold_as_complete(self):
        """Claim: a row with a long-context surcharge is exported under its ids
        with no category priced, and its source and the table header name the
        surcharge, so a fully measured request over the threshold is never a
        complete estimate. Rejects the short-prompt rates exported as
        unconditional prices: 200,000 uncached input and 1,000 output tokens
        would read complete at $0.0205 against a list price of $0.1025."""
        with FixtureRoster(SURCHARGED_MODELS) as root:
            export = price_export(root)
            text = tapes_table(export)
        table = {model["id"]: model for model in tomllib.loads(text)["models"]}
        self.assertEqual(table["short-1"]["aliases"], ["vendor-short-1"])
        self.assertEqual(table["short-1"]["per_million"], {})
        amount, missing = list_price(table["short-1"]["per_million"], {"uncached_input": 200_000, "output": 1_000})
        self.assertTrue(missing, f"priced complete at {amount}")
        self.assertIn("100,000 input tokens", table["short-1"]["source"])
        self.assertIn("tapes-price-table/1 cannot express", table["short-1"]["source"])
        self.assertIn("# Prices left out for short-1: ", text)
        self.assertEqual(table["flat-2"]["per_million"], {"uncached_input": 2.0, "output": 6.0})
        self.assertIn("prices left out: short-1: ", readable_table(export))

    def test_lint_refuses_a_malformed_surcharge(self):
        """Claim: a surcharge needs a positive whole-token threshold and
        input, cache and output multipliers of at least one, and only on a
        priced row. Rejects a surcharge the export could not describe."""
        cases = {
            'threshold_input_tokens = 0, input_multiplier = 2.0, cache_multiplier = 2.0, output_multiplier = 1.5':
                "threshold_input_tokens must be a positive whole number",
            'threshold_input_tokens = 272000, input_multiplier = 2.0, output_multiplier = 1.5':
                "long_context_surcharge.cache_multiplier must be a finite number of at least one",
            'threshold_input_tokens = 272000, input_multiplier = 0.5, cache_multiplier = 2.0, output_multiplier = 1.5':
                "long_context_surcharge.input_multiplier must be a finite number of at least one",
        }
        for body, expected in cases.items():
            with self.subTest(expected=expected):
                models = tomllib.loads(f'[[model]]\nid = "x"\napi_price_per_million = {{ input = 1.0 }}\n'
                                       f'api_price_read = "2026-09-01"\nlong_context_surcharge = {{ {body} }}\n')["model"]
                problems = price_problems(models)
                self.assertTrue(any(expected in problem for problem in problems), problems)
        unpriced = tomllib.loads('[[model]]\nid = "x"\nlong_context_surcharge = { threshold_input_tokens = 1, '
                                 'input_multiplier = 2.0, cache_multiplier = 2.0, output_multiplier = 2.0 }\n')["model"]
        self.assertTrue(price_problems(unpriced))

    def test_the_roster_exports_every_priced_row_and_no_surcharged_price(self):
        """Claim: every priced roster row is dated and exported, and every row
        with a long-context surcharge exports with no category priced. Rejects
        a roster row left out of the table, and a surcharged row whose
        short-prompt rate would price a long request as complete."""
        models = tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]
        priced = {model["id"]: model for model in models if "api_price_per_million" in model}
        rows = {row["id"]: row for row in price_export(ROOT)["models"]}
        self.assertEqual(set(rows), set(priced))
        for model_id, model in priced.items():
            with self.subTest(model=model_id):
                self.assertIn("api_price_read", model)
                if "long_context_surcharge" in model:
                    self.assertEqual(rows[model_id]["per_million"], {})
                else:
                    self.assertTrue(rows[model_id]["per_million"])


if __name__ == "__main__":
    unittest.main()
