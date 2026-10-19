"""Every roster price carries the date it was read, and every priced row is
exported, a row whose list price rises above a prompt-size threshold with the
term that prices it."""

import pathlib
import sys
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from price_export import price_export, price_problems  # noqa: E402


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

    def test_the_roster_exports_every_priced_row(self):
        """Claim: every priced roster row is dated and exported with prices,
        and every row with a long-context surcharge carries its term. Rejects
        a roster row left out of the table, and a surcharged row whose
        short-prompt rate would price a long request as complete."""
        models = tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]
        priced = {model["id"]: model for model in models if "api_price_per_million" in model}
        rows = {row["id"]: row for row in price_export(ROOT)["models"]}
        self.assertEqual(set(rows), set(priced))
        for model_id, model in priced.items():
            with self.subTest(model=model_id):
                self.assertIn("api_price_read", model)
                self.assertTrue(rows[model_id]["per_million"])
                self.assertEqual(rows[model_id]["long_context"] is not None, "long_context_surcharge" in model)


if __name__ == "__main__":
    unittest.main()
