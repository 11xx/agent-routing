"""What the read-only verbs print from the fixture data: prices, agents, doctrine and the CLI."""

import subprocess
import tomllib
import unittest

from fixture import ROOT

import claude_agents
import doctrine
import price_export
import stores


def run(*args):
    return subprocess.run([str(ROOT / "bin" / "agent-routing"), *args], capture_output=True, text=True)


class PriceTest(unittest.TestCase):
    def test_the_tapes_table_carries_list_prices_and_their_terms(self):
        """Claim: the tapes table prices each priced model from the catalog,
        maps cache prices to tapes categories, and carries a surcharge as a
        long-context term. Rejects a table that drops a term or misnames a
        category."""
        table = tomllib.loads(price_export.tapes_table(price_export.price_export(ROOT)))
        by_id = {row["id"]: row for row in table["models"]}
        self.assertEqual(by_id["nw-atlas-2"]["per_million"],
                         {"uncached_input": 4.0, "cache_read": 0.4, "cache_write_5m": 5.0,
                          "cache_write_1h": 8.0, "output": 20.0})
        self.assertEqual(by_id["nw-swift-2"]["long_context"]["above_prompt_tokens"], 100000)
        self.assertEqual(by_id["orbit-flash"]["per_million"],
                         {"uncached_input": 0.1, "cache_read": 0.01, "output": 0.4})
        self.assertIn("ts-3-prime", by_id)
        self.assertNotIn("ts-2-prime", by_id)


class ClaudeAgentsTest(unittest.TestCase):
    def test_one_agent_per_stable_claude_seat_pinned_to_its_alias(self):
        """Claim: the bundle writes one agent for each stable claude seat, its
        model the reach row's agent alias, and pins it under the consumer the
        policy marks as generated from claude-agents. Rejects an agent for a
        seat another backend holds, or a pin under a hard-coded consumer."""
        bundle = claude_agents.claude_agent_bundle(ROOT)
        self.assertEqual(sorted(bundle["files"]), ["agents/extract-swift.md", "agents/implement-atlas-high.md",
                                                   "agents/implement-atlas.md", "agents/plan-sage.md",
                                                   "agents/review-atlas.md", "consumers-pins.toml"])
        self.assertIn("model: atlas\neffort: medium\n", bundle["files"]["agents/implement-atlas.md"])
        self.assertEqual({pin["consumer"] for pin in bundle["pins"]}, {"harness-agents"})


class DoctrineTest(unittest.TestCase):
    def test_doctrine_renders_principles_then_the_stores(self):
        """Claim: the doctrine is the principles file followed by every
        profile's seats with their when, why and since, the bans with their
        reasons, and the catalog with its note counts. Rejects a doctrine that
        drifts from the stores."""
        text = doctrine.render(ROOT)
        self.assertTrue(text.startswith((ROOT / doctrine.PRINCIPLES).read_text().rstrip()))
        self.assertIn("| atlas-high | claude | nw-atlas-2 · high | stable | Implementation that needs the head "
                      "model's standing tier. | High is the head model's working tier. | 2030-01-03 |", text)
        self.assertIn("| nw-atlas-2 · max | Fixture ban: the top tier buys nothing over xhigh. |", text)
        self.assertIn("| orbit-flash | orbit | active | max 1/1, low 1/1 | 0.1 / 0.4 | 1 |", text)

    def test_the_delegation_view_is_canonical_rows(self):
        """Claim: the delegation view prints the backend, reach and effort
        rows in the catalog's canonical form, then the pools. Rejects a view
        whose rows differ from the store."""
        text = doctrine.delegation(ROOT)
        catalog = (ROOT / stores.CATALOG).read_text()
        self.assertIn('[[effort_support]]\nmodel = "orbit-flash"\nbackend = "pi"\nefforts = ["low", "high", "max"]\n',
                      text)
        self.assertIn('[[reach]]\nmodel = "orbit-flash"\nbackend = "pi"\nprovider = "flat-pool"\n'
                      'backend_model = "orbit-flash-0101"\n', catalog)
        self.assertIn('[[pool]]\nprovider = "flat-pool"', text)


class CommandTest(unittest.TestCase):
    def test_the_dispatcher_locates_and_prints_the_stores(self):
        """Claim: `dir` names the data directory, `models` and `profiles` print
        the catalog and the policy byte for byte. Rejects a dispatcher that
        reads the live data or a stale path."""
        self.assertEqual(run("dir").stdout, f"{ROOT / stores.DATA}\n")
        self.assertEqual(run("models").stdout, (ROOT / stores.CATALOG).read_text())
        self.assertEqual(run("profiles").stdout, (ROOT / stores.POLICY).read_text())

    def test_check_exits_non_zero_only_on_a_prohibited_tier(self):
        """Claim: `check` exits 1 on a prohibited tier and 0 otherwise, naming
        a superseded model's successor. Rejects a check that passes a ban."""
        banned = run("check", "nw-atlas-2", "max")
        self.assertEqual((banned.returncode, banned.stderr.splitlines()[0]), (1, "prohibited: nw-atlas-2 at max"))
        superseded = run("check", "nw-atlas-1")
        self.assertEqual((superseded.returncode, superseded.stdout.strip()),
                         (0, "superseded: nw-atlas-1 — its successor is nw-atlas-2"))


if __name__ == "__main__":
    unittest.main()
