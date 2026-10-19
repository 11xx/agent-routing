"""Every roster price carries the date it was read: a price with no read date
cannot be placed in time, so it does not enter the roster."""

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

    def test_the_roster_exports_every_priced_row(self):
        """Claim: every priced roster row is dated and exported. Rejects a
        roster row left out of the table."""
        models = tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]
        priced = {model["id"]: model for model in models if "api_price_per_million" in model}
        rows = {row["id"]: row for row in price_export(ROOT)["models"]}
        self.assertEqual(set(rows), set(priced))
        for model_id, model in priced.items():
            with self.subTest(model=model_id):
                self.assertIn("api_price_read", model)


if __name__ == "__main__":
    unittest.main()
