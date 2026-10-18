"""The roster's API prices export as a tapes-price-table/1 file: each priced
row under its roster id with the ids harnesses record as aliases, dated by
its read date, pricing only the categories the row prices, and a row with no
read date left out and named."""

import datetime
import pathlib
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from price_export import CATEGORIES, price_export, price_problems, tapes_table  # noqa: E402

FIXTURE_MODELS = '''
[[model]]
id = "alpha-1"
family = "fixture"
aliases = ["vendor-alpha-1"]
api_price_per_million = { input = 3.0, cached_input = 0.3, cache_write = 3.75, cache_write_1h = 6.0, output = 15.0 }
api_price_read = "2026-10-01"

[[model]]
id = "beta-2"
family = "fixture"
api_price_per_million = { cache_miss_input = 0.3, cache_hit_input = 0.006, output = 1.2 }
api_price_read = "2026-09-01"

[[model]]
id = "gamma-3"
family = "fixture"
api_price_per_million = { input = 2.0, output = 6.0 }
api_price_undated = "no read date in the fixture"

[[model]]
id = "delta-4"
family = "fixture"
'''

FIXTURE_PROFILES = '''
[[profile]]
id = "generate"
backends = ["pi"]
provider = "fixture-pool"
model = "beta-2"
backend_model = "provider/beta-2"
effort = "high"
'''


class FixtureRoster:
    def __init__(self, models: str = FIXTURE_MODELS):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name)
        routing = self.root / "routing"
        routing.mkdir()
        (routing / "models.toml").write_text(models)
        (routing / "profiles.toml").write_text(FIXTURE_PROFILES)
        (routing / "delegation.toml").write_text("")

    def __enter__(self):
        return self.root

    def __exit__(self, *_):
        self.directory.cleanup()


class PriceExportTest(unittest.TestCase):
    def test_a_fixture_roster_exports_mapped_dated_recorded_rows(self):
        """Claim: roster categories map onto tapes' (input, cache-miss input ->
        uncached_input; cached and cache-hit input -> cache_read; cache_write ->
        cache_write_5m), recorded ids are the row's aliases and the
        backend_model routes bind to it, the date is the row's read date, an
        undated row is left out with its reason, and an unpriced row is not
        listed. Rejects an export that invents a price or a date."""
        with FixtureRoster() as root:
            export = price_export(root)
        rows = {row["id"]: row for row in export["models"]}
        self.assertEqual(set(rows), {"alpha-1", "beta-2"})
        self.assertEqual(rows["alpha-1"]["per_million"], {
            "uncached_input": 3.0, "cache_read": 0.3, "cache_write_5m": 3.75,
            "cache_write_1h": 6.0, "output": 15.0,
        })
        self.assertEqual(rows["alpha-1"]["aliases"], ["vendor-alpha-1"])
        self.assertEqual(rows["alpha-1"]["effective"], "2026-10-01")
        self.assertEqual(rows["beta-2"]["per_million"],
                         {"uncached_input": 0.3, "cache_read": 0.006, "output": 1.2})
        self.assertEqual(rows["beta-2"]["unpriced"], ["cache_write_5m", "cache_write_1h"])
        self.assertEqual(rows["beta-2"]["aliases"], ["provider/beta-2"])
        self.assertEqual(export["omitted"], [{"id": "gamma-3", "reason": "no read date in the fixture"}])

    def test_the_table_is_tapes_price_table_toml(self):
        """Claim: the written table parses as TOML in tapes' shape: schema,
        currency, and per model an id, aliases, a date `effective`, a source
        and per-million prices under tapes' category names only. Rejects a
        string date or a roster key in the output."""
        with FixtureRoster() as root:
            table = tomllib.loads(tapes_table(price_export(root)))
        self.assertEqual(table["schema"], "tapes-price-table/1")
        self.assertEqual(table["currency"], "USD")
        self.assertEqual([model["id"] for model in table["models"]], ["alpha-1", "beta-2"])
        for model in table["models"]:
            self.assertEqual(set(model) - {"aliases"}, {"id", "effective", "source", "per_million"})
            self.assertIsInstance(model["effective"], datetime.date)
            self.assertLessEqual(set(model["per_million"]), set(CATEGORIES))
        self.assertEqual(table["models"][1]["effective"], datetime.date(2026, 9, 1))

    def test_lint_refuses_undated_and_unknown_prices(self):
        """Claim: a price without a read date or a stated reason, a malformed
        date, an unknown or doubled category key, a negative price, and a date
        without a price are each refused by name. Rejects a roster price that
        reaches the export undated or under a key tapes cannot place."""
        cases = {
            '{ input = 1.0 }': "needs api_price_read",
            '{ input = 1.0 }\napi_price_read = "2026-9-1"': "must be a YYYY-MM-DD date",
            '{ input = 1.0, cache_read = 0.1 }\napi_price_read = "2026-09-01"': "unknown api_price_per_million key 'cache_read'",
            '{ input = 1.0, cache_miss_input = 1.0 }\napi_price_read = "2026-09-01"': "price the same category",
            '{ output = -1.0 }\napi_price_read = "2026-09-01"': "must be a finite number of at least zero",
            '{ input = 1.0 }\napi_price_read = "2026-09-01"\napi_price_undated = "x"': "needs api_price_read",
        }
        for body, expected in cases.items():
            with self.subTest(expected=expected):
                models = tomllib.loads(f'[[model]]\nid = "x"\napi_price_per_million = {body}\n')["model"]
                problems = price_problems(models)
                self.assertTrue(any(expected in problem for problem in problems), problems)
        stray = tomllib.loads('[[model]]\nid = "x"\napi_price_read = "2026-09-01"\n')["model"]
        self.assertTrue(price_problems(stray))

    def test_the_roster_exports_and_lints(self):
        """Claim: the real roster passes the price lint, every exported Claude
        row prices one-hour cache writes at twice its input and five-minute
        writes at 1.25 times, and the Opus row answers to the id Claude
        records. Rejects an export with the one-hour write left out, which
        leaves a Claude estimate unpriced on its one-hour writes."""
        models = tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]
        self.assertEqual(price_problems(models), [])
        rows = {row["id"]: row for row in price_export(ROOT)["models"]}
        for model in models:
            if model.get("family") == "claude" and model["id"] in rows:
                prices = rows[model["id"]]["per_million"]
                with self.subTest(model=model["id"]):
                    self.assertAlmostEqual(prices["cache_write_5m"], 1.25 * prices["uncached_input"])
                    self.assertAlmostEqual(prices["cache_write_1h"], 2 * prices["uncached_input"])
        self.assertIn("claude-opus-5-5", rows["opus-5.5"]["aliases"])

    def test_the_command_writes_the_table(self):
        """Claim: `agent-routing prices --format tapes --output FILE` writes the
        table and the bare command prints a readable one naming omissions."""
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "prices.toml"
            result = subprocess.run([ROOT / "bin/agent-routing", "prices", "--format", "tapes", "--output", output],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(tomllib.loads(output.read_text())["schema"], "tapes-price-table/1")
        result = subprocess.run([ROOT / "bin/agent-routing", "prices"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("model\tread\tuncached_input"))
        self.assertIn("not exported: ", result.stdout)


if __name__ == "__main__":
    unittest.main()
