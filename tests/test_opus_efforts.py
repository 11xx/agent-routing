"""Opus 5.5's effort ladder: four stable tiers, a banned max, and the Claude defaults."""

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
from routing_profiles import RouteRefusal, resolve, seats_view, validate_selection

STABLE_TIERS = ("low", "medium", "high", "xhigh")


def opus_tiers(root=ROOT):
    models = tomllib.loads((root / "routing/models.toml").read_text())["model"]
    opus = next(model for model in models if model["id"] == "opus-5.5")
    return {tier["effort"]: tier for tier in opus["effort"]}


class OpusEffortsTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        for name in ("routing", "templates"):
            shutil.copytree(ROOT / name, root / name)
        return root

    def test_low_through_xhigh_are_stable_seated_review_tiers(self):
        # Rejects any of the four carrying explicit-only, a ban, or no seat.
        tiers = opus_tiers()
        seated = {seat["effort"] for seat in seats_view(ROOT)["seats"]
                  if seat["roster_model"] == "opus-5.5" and seat["stability"] == "stable"}
        for effort in STABLE_TIERS:
            with self.subTest(effort=effort):
                tier = tiers[effort]
                self.assertNotIn("status", tier)
                self.assertFalse(tier["use"].startswith("prohibited"))
                self.assertIn("review_tier", tier)
                self.assertIn(effort, seated)
                checked = subprocess.run([ROOT / "bin/agent-routing", "check", "claude-opus-5-5", effort],
                                         capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertIn(f"not prohibited: opus-5.5 at {effort}", checked.stdout)

    def test_review_tiers_never_fall_as_effort_rises(self):
        # Rejects an ordering where a deeper tier could be reviewed below a shallower one.
        tiers = opus_tiers()
        ladder = [tiers[effort]["review_tier"] for effort in STABLE_TIERS]
        self.assertEqual(ladder, sorted(ladder))
        self.assertGreaterEqual(tiers["max"]["author_floor"], ladder[-1])

    def test_check_refuses_max_under_every_name(self):
        # Rejects max answering as explicit-only, which would let a direct request reach it.
        for name in ("opus-5.5", "opus-5-5", "claude-opus-5-5"):
            with self.subTest(name=name):
                checked = subprocess.run([ROOT / "bin/agent-routing", "check", name, "max"],
                                         capture_output=True, text=True)
                self.assertEqual(checked.returncode, 1, checked.stdout)
                self.assertIn("prohibited: opus-5.5 at max", checked.stderr)

    def test_operator_named_selection_cannot_reach_max(self):
        # Rejects an operator-named max passing as an explicit-only selection.
        with self.assertRaises(RouteRefusal) as caught:
            validate_selection(ROOT, "implement", "claude", "opus-5.5", "max", "anthropic",
                               "operator directed", allow_experimental=True, operator_named=True)
        self.assertEqual(caught.exception.kind, "prohibited")

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

    def test_claude_implementation_defaults_to_opus_low(self):
        # Rejects any other tier holding the default Claude implementer seat.
        route = resolve(ROOT, "implement", "claude")
        self.assertEqual((route["model"], route["effort"], route["stability"]),
                         ("claude-opus-5-5", "low", "stable"))
        completed = subprocess.run([ROOT / "bin/agent-routing", "resolve", "implement", "--backend", "claude",
                                    "--json"], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["effort"], "low")

    def test_implementation_keeps_every_stable_tier_selectable(self):
        # Rejects a stable tier a lead can no longer name for implementation.
        efforts = {}
        for variant in ("opus-low", "opus-medium", "opus-high", "opus-xhigh"):
            route = resolve(ROOT, "implement", "claude", variant_id=variant)
            self.assertEqual(route["stability"], "stable")
            efforts[variant] = route["effort"]
        self.assertEqual(efforts, {"opus-low": "low", "opus-medium": "medium",
                                   "opus-high": "high", "opus-xhigh": "xhigh"})

    def test_head_seat_resolves_to_opus_high(self):
        # Rejects an absent head binding or one at another tier.
        head = seats_view(ROOT)["head_default"]
        self.assertIsNotNone(head)
        self.assertEqual((head["model"], head["effort"], head["backend"]), ("claude-opus-5-5", "high", "claude"))

    def test_first_party_claude_review_stays_at_xhigh(self):
        # Rejects the deep-review seat drifting with the head's tier.
        route = resolve(ROOT, "review", "claude")
        self.assertEqual((route["model"], route["effort"]), ("claude-opus-5-5", "xhigh"))


if __name__ == "__main__":
    unittest.main()
