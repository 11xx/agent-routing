import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from claude_agents import claude_agent_bundle
from routing_profiles import RouteRefusal, resolve


class ClaudeAgentsTest(unittest.TestCase):
    def test_every_stable_claude_route_has_a_definition_and_matching_pin(self):
        bundle = claude_agent_bundle(ROOT)
        profiles = tomllib.loads((ROOT / "routing/profiles.toml").read_text())["profile"]
        expected = {(profile["id"], None if route is profile else route["id"])
                    for profile in profiles for route in [profile, *profile.get("variant", [])]
                    if "claude" in route["backends"] and route["stability"] == "stable"}
        self.assertEqual({(pin["profile"], pin.get("variant")) for pin in bundle["pins"]}, expected)
        self.assertEqual(tomllib.loads(bundle["files"]["consumers-pins.toml"])["pin"], bundle["pins"])
        for pin in bundle["pins"]:
            route = resolve(ROOT, pin["profile"], pin["backend"], variant_id=pin.get("variant"))
            content = bundle["files"][f"agents/{pin['path']}"]
            self.assertIn(f"model: {pin['model']}\n", content)
            self.assertIn(f"effort: {route['effort']}\n", content)
            self.assertNotIn(route["model"], content)
            self.assertTrue(pin["generated"])

    def test_each_stable_opus_tier_has_one_implementer_definition(self):
        bundle = claude_agent_bundle(ROOT, profile_id="implement")
        self.assertEqual({pin["path"]: pin["effort"] for pin in bundle["pins"]},
                         {"implement-opus-low.md": "low", "implement-opus-medium.md": "medium",
                          "implement-opus-high.md": "high", "implement-opus-xhigh.md": "xhigh"})
        default = resolve(ROOT, "implement", "claude")
        self.assertEqual(default["profile"], "implement:opus-low")
        self.assertIn("model: opus\neffort: low\n", bundle["files"]["agents/implement-opus-low.md"])
        self.assertFalse(any(pin.get("allow_experimental") for pin in bundle["pins"]))

    def test_trial_agents_require_explicit_opt_in(self):
        self.assertNotIn("agents/computer-use-opus.md", claude_agent_bundle(ROOT)["files"])
        bundle = claude_agent_bundle(ROOT, profile_id="computer-use", variant_id="opus",
                                     allow_experimental=True)
        self.assertIn("agents/computer-use-opus.md", bundle["files"])
        self.assertTrue(bundle["pins"][0]["allow_experimental"])
        with self.assertRaises(RouteRefusal):
            claude_agent_bundle(ROOT, profile_id="computer-use", variant_id="opus")

    def test_prohibition_refuses_emission_before_any_file_is_written(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for name in ("routing", "templates"):
                shutil.copytree(ROOT / name, root / name)
            models = root / "routing/models.toml"
            text = models.read_text()
            start = text.index('id = "opus-5.5"')
            tier = text.index('effort = "xhigh"', start)
            use = text.index('use = "', tier)
            models.write_text(text[:use] + 'use = "PROHIBITED: fixture ban"\n' + text[text.index('\n', use) + 1:])
            with self.assertRaises(RouteRefusal):
                claude_agent_bundle(root)

    def test_selected_route_and_pin_are_consistent(self):
        bundle = claude_agent_bundle(ROOT, profile_id="implement", variant_id="opus-low")
        self.assertEqual(set(bundle["files"]), {"agents/implement-opus-low.md", "consumers-pins.toml"})
        self.assertEqual(len(bundle["pins"]), 1)
        self.assertIn("Stay inside the named worktree", bundle["files"]["agents/implement-opus-low.md"])

    def test_cli_stages_and_checks_without_implicit_harness_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "bundle"
            command = [ROOT / "bin/agent-routing", "emit", "claude-agents", "--profile", "implement",
                       "--variant", "opus-xhigh", "--output-dir", output]
            emitted = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(emitted.returncode, 0, emitted.stderr)
            self.assertEqual(json.loads(emitted.stdout)["schema"], "agent-routing-claude-agents/1")
            checked = subprocess.run([*command, "--check"], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            path = output / "agents/implement-opus-xhigh.md"
            path.write_text(path.read_text().replace("effort: xhigh", "effort: max"))
            before = path.read_bytes()
            checked = subprocess.run([*command, "--check"], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 1)
            self.assertEqual(path.read_bytes(), before)
            self.assertIn("generated-drift", checked.stderr)
