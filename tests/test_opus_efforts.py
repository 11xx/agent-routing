"""A prohibited tier is refused wherever it is reached: the check, a declared route and an emitted agent."""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "lib"))
sys.path.insert(0, str(REPOSITORY / "tests"))
from roster import ROOT  # noqa: E402
from claude_agents import claude_agent_bundle
from routing_profiles import RouteRefusal, resolve


class OpusEffortsTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        for name in ("routing", "templates"):
            shutil.copytree(ROOT / name, root / name)
        return root

    def test_check_refuses_max_under_every_name(self):
        # Rejects max answering as explicit-only, which would let a direct request reach it.
        for name in ("opus-5.5", "opus-5-5", "claude-opus-5-5"):
            with self.subTest(name=name):
                checked = subprocess.run([ROOT / "bin/agent-routing", "check", name, "max"],
                                         capture_output=True, text=True)
                self.assertEqual(checked.returncode, 1, checked.stdout)
                self.assertIn("prohibited: opus-5.5 at max", checked.stderr)

    def test_resolve_and_emit_refuse_a_route_declared_at_max(self):
        # Rejects a max route being refused only as explicit-only rather than as banned.
        root = self.fixture_root()
        profiles = root / "routing/profiles.toml"
        text = profiles.read_text()
        anchor = text.index('[[profile]]\nid = "generate"')
        profiles.write_text(text[:anchor] + '''  [[profile.variant]]
  id = "opus-max"
  provider = "anthropic"
  model = "opus-5.5"
  backend_model = "claude-opus-5-5"
  effort = "max"
  stability = "experimental"
  backends = ["claude"]

''' + text[anchor:])
        with self.assertRaises(RouteRefusal) as resolved:
            resolve(root, "implement", "claude", variant_id="opus-max", allow_experimental=True)
        self.assertIn("opus-5.5 max is prohibited", str(resolved.exception))
        with self.assertRaises(RouteRefusal) as emitted:
            claude_agent_bundle(root, profile_id="implement", variant_id="opus-max", allow_experimental=True)
        self.assertIn("opus-5.5 max is prohibited", str(emitted.exception))


if __name__ == "__main__":
    unittest.main()
