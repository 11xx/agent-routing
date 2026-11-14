"""The command contracts: refusals, route filters and Claude agent emission, over the fixture data."""

import json
import pathlib
import tempfile
import unittest

from fixture import ROOT, edit, run_command, scratch

import claude_agents
import stores
from routing_profiles import RouteRefusal, resolve, routes_view

TRIAL_SEAT = ('[[seat]]\nprofile = "implement"\nvariant = "atlas-trial"\nbackends = ["claude"]\n'
              'provider = "northwind-plan"\nmodel = "nw-atlas-2"\neffort = "low"\nstability = "experimental"\n'
              'when = "A trial of the low tier."\nwhy = "Unmeasured."\nsince = "2030-01-03"\n\n')


def command(name, *argv, root=ROOT):
    return run_command(root / "bin" / name, list(argv))


class RefusalTest(unittest.TestCase):
    def test_a_refusal_keeps_stdout_empty_and_puts_its_payload_on_stderr(self):
        """Claim: resolve, validate and assess exit 1 on a refusal with
        nothing on stdout and the refusal payload, kind included, as the last
        line of stderr. Rejects a caller parsing a refusal as an answer."""
        cases = {
            "resolve-route": (["nowhere", "--backend", "codex", "--json"], "unknown-profile"),
            "validate-selection": (["--profile", "implement", "--backend", "claude", "--model", "nw-atlas-2",
                                    "--effort", "max", "--provider", "northwind-plan", "--reason", "fixture",
                                    "--json"], "prohibited"),
            "assess-review": (["--reviewer", "nobody#high", "--author", "ts-3-core#max", "--json"],
                              "unknown-coordinate"),
        }
        for name, (argv, kind) in cases.items():
            with self.subTest(command=name):
                code, out, err = command(name, *argv)
                self.assertEqual((code, out), (1, ""))
                payload = json.loads(err.strip().splitlines()[-1])
                self.assertEqual((payload["schema"], payload["kind"]), ("agent-routing-refusal/1", kind))

    def test_an_unsupported_backend_names_the_routes_it_has(self):
        """Claim: a profile with no seat on the backend is refused naming
        the backend. Rejects answering with another backend's seat."""
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "survey", "claude")
        self.assertEqual(caught.exception.kind, "unsupported-backend")

    def test_routes_require_json(self):
        """Claim: the routes listing is machine output only. Rejects a text
        form a caller could scrape."""
        code, out, _ = command("list-routes")
        self.assertEqual((code, out), (2, ""))


class RoutesTest(unittest.TestCase):
    def test_the_listing_is_every_plain_resolution(self):
        """Claim: each listed route is exactly what resolve answers for it
        without opt-ins, and a seat needing an opt-in is not listed. Rejects a
        listing that disagrees with resolve or sells an experimental seat."""
        routes = routes_view(ROOT)["routes"]
        for route in routes:
            with self.subTest(route=route):
                answer = resolve(ROOT, route["profile"], route["backend"], variant_id=route["variant"])
                self.assertEqual({key: answer[key] for key in ("provider", "model", "effort", "stability")},
                                 {key: route[key] for key in ("provider", "model", "effort", "stability")})
        self.assertNotIn(("implement", "trial"), {(route["profile"], route["variant"]) for route in routes})
        self.assertIn(("survey", None, "pi"), {(route["profile"], route["variant"], route["backend"])
                                               for route in routes})

    def test_filters_keep_the_matching_routes_and_every_prohibition(self):
        """Claim: --backend and --profile keep exactly the matching routes and
        never drop a prohibited tier. Rejects a filter that hides a ban."""
        whole = routes_view(ROOT)
        for filters in ({"backend": "pi"}, {"profile_id": "review"}, {"backend": "claude", "profile_id": "plan"},
                        {"backend": "absent"}):
            with self.subTest(filters=filters):
                expected = [route for route in whole["routes"]
                            if all(route["profile" if key == "profile_id" else key] == value
                                   for key, value in filters.items())]
                self.assertEqual(routes_view(ROOT, **filters), {**whole, "routes": expected})
        code, out, _ = command("list-routes", "--json", "--backend", "pi")
        self.assertEqual((code, json.loads(out)), (0, routes_view(ROOT, backend="pi")))


class AgentEmissionTest(unittest.TestCase):
    def test_a_trial_agent_needs_the_explicit_opt_in(self):
        """Claim: an experimental Claude seat is left out of the default
        bundle, refused when named without --allow-experimental, and emitted
        with it, its pin marked. Rejects a trial agent installed by default."""
        root = scratch(self, code=True)
        edit(root, stores.POLICY, '[[seat]]\nprofile = "implement"\nvariant = "trial"',
             TRIAL_SEAT + '[[seat]]\nprofile = "implement"\nvariant = "trial"')
        self.assertNotIn("agents/implement-atlas-trial.md", claude_agents.claude_agent_bundle(root)["files"])
        with self.assertRaises(RouteRefusal) as caught:
            claude_agents.claude_agent_bundle(root, profile_id="implement", variant_id="atlas-trial")
        self.assertEqual(caught.exception.kind, "stability")
        bundle = claude_agents.claude_agent_bundle(root, profile_id="implement", variant_id="atlas-trial",
                                                   allow_experimental=True)
        self.assertEqual(bundle["pins"], [{"consumer": "harness-agents", "path": "implement-atlas-trial.md",
                                           "model": "atlas", "effort": "low", "profile": "implement",
                                           "backend": "claude", "generated": True, "variant": "atlas-trial",
                                           "allow_experimental": True}])

    def test_check_compares_without_writing_and_names_drift(self):
        """Claim: emit writes the bundle under --output-dir, --check passes on
        that tree and refuses an edited file by name, and invalid data writes
        nothing. Rejects a check that rewrites what it compares, or an emit
        that leaves a partial tree."""
        output = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory())) / "out"
        self.assertEqual(command("emit-claude-agents", "claude-agents", "--output-dir", str(output))[0], 0)
        self.assertEqual(command("emit-claude-agents", "claude-agents", "--output-dir", str(output), "--check")[0], 0)
        agent = output / "agents" / "plan-sage.md"
        agent.write_text(agent.read_text() + "drift\n")
        code, _, err = command("emit-claude-agents", "claude-agents", "--output-dir", str(output), "--check")
        self.assertEqual(code, 1)
        self.assertIn("generated content differs: agents/plan-sage.md", err)
        self.assertTrue(agent.read_text().endswith("drift\n"))
        root = scratch(self, code=True)
        edit(root, stores.POLICY, 'model = "nw-sage-2"\neffort = "high"\nstability = "stable"',
             'model = "nw-atlas-2"\neffort = "max"\nstability = "stable"')
        fresh = output.parent / "fresh"
        code, _, _ = run_command(root / "bin" / "emit-claude-agents",
                                 ["claude-agents", "--output-dir", str(fresh)])
        self.assertEqual((code, fresh.exists()), (1, False))


if __name__ == "__main__":
    unittest.main()
