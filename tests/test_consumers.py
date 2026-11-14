"""The on-demand consumer lint, over a scratch tree of sibling repositories."""

import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from fixture import ROOT

import claude_agents


class ConsumerLintTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.code = pathlib.Path(temporary.name)
        settings = self.code / "declared" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"$route": "implement"}) + "\n")
        sources = [{"id": "settings", "path": str(settings), "checks": ["roster-literals", "pi-route"]}]
        self.harness = self.code / "agent-harness"
        self.harness.write_text(f"#!/usr/bin/env python3\nprint({json.dumps(sources)!r})\n")
        self.harness.chmod(0o700)
        self.agents = self.code / "fixture-harness" / "agents"
        self.agents.mkdir(parents=True)
        (self.agents / "proxy.md").write_text("---\nmodel: swift\neffort: low\n---\nRelay the command.\n")
        bundle = claude_agents.claude_agent_bundle(ROOT, profile_id="implement", variant_id="atlas")
        (self.agents / "implement-atlas.md").write_text(bundle["files"]["agents/implement-atlas.md"])

    def lint(self):
        environment = {**os.environ, "AGENT_CODE_ROOT": str(self.code), "AGENT_HARNESS_BIN": str(self.harness)}
        return subprocess.run([ROOT / "bin" / "lint-consumers"], capture_output=True, text=True, env=environment)

    def test_a_clean_tree_passes_and_each_pin_kind_is_caught(self):
        """Claim: a consumer tree whose agents match their pins passes; a
        catalog id in a consumer source, an edited proxy model and a generated
        agent that drifts from its route each fail, naming the file. Rejects
        a lint that lets a concrete model pin into a consumer."""
        clean = self.lint()
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
        (self.agents / "notes.md").write_text("Use orbit-flash for this.\n")
        (self.agents / "proxy.md").write_text("---\nmodel: atlas\neffort: low\n---\nRelay the command.\n")
        generated = self.agents / "implement-atlas.md"
        generated.write_text(generated.read_text() + "An extra line.\n")
        result = self.lint()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(f"{self.agents / 'notes.md'}:1: concrete route literal: orbit-flash", result.stdout)
        self.assertIn(f"{self.agents / 'proxy.md'}:2: delegation source pins model frontmatter", result.stdout)
        self.assertIn(f"{generated}: generated agent differs from the resolved route template", result.stdout)

    def test_an_accessor_missing_an_expected_source_fails(self):
        """Claim: an accessor that reports fewer sources than the policy's
        floor fails before any file is read. Rejects a lint that passes by
        finding nothing to check."""
        self.harness.write_text("#!/usr/bin/env python3\nprint('[]')\n")
        result = self.lint()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("instructions: missing expected delegation sources: settings", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
