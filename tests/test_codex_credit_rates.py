"""Codex credit rates track the API price they are weighted against.

The roster's `[quota].weighting` states that every token class of a Codex row
with a published API price costs 25 credits per API dollar, and the quota
doctrine converts benchmark cash into Codex credits on that ratio. A credit rate
left behind when the API price moves breaks that conversion silently.
"""

import math
import pathlib
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CREDITS_PER_API_DOLLAR = 25.0


class CodexCreditRatesTest(unittest.TestCase):
    def test_every_credited_row_costs_25_credits_per_api_dollar(self):
        """Claim: each Codex row's input, cached-input and output credit
        rates are 25 times its short-context API price, the ratio the quota
        weighting states. Rejects a row whose credits still price an earlier
        API rate, such as GPT-5.6 Sol at 125/12.5/750 credits against a
        $4/$0.40/$20 API price."""
        models = tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]
        credited = [model for model in models if "subscription_credits_per_million" in model]
        self.assertTrue(credited)
        for model in credited:
            prices = model["api_price_per_million"]
            for token_class, credits in model["subscription_credits_per_million"].items():
                with self.subTest(model=model["id"], token_class=token_class):
                    self.assertTrue(
                        math.isclose(credits, prices[token_class] * CREDITS_PER_API_DOLLAR),
                        f"{credits} credits against ${prices[token_class]}",
                    )


if __name__ == "__main__":
    unittest.main()
