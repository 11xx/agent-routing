"""The roster's prices export as a tapes-price-table/2 file carrying every
term the roster records: a long-context surcharge as a long-context term for
API per-token billing only."""

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
            case.assertEqual(set(window), {"from", "until", "per_million"}, model["id"])


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


if __name__ == "__main__":
    unittest.main()
