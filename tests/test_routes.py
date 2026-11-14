"""A picker sees every plain resolve coordinate and exactly its resolved tuple."""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "lib"))
sys.path.insert(0, str(REPOSITORY / "tests"))
from roster import ROOT
from routing_profiles import RouteRefusal, resolve, route_version, routes_view, seats_view


FIXTURE = {
    "models.toml": '''
[review]
clearance = 2
[[model]]
id = "inkstone"
family = "paper-lab"
[[model.effort]]
effort = "low"
rank = 1
floor = 1
seat_rank = { paper = 1 }
[[model.effort]]
effort = "high"
rank = 2
floor = 2
seat_rank = { paper = 2 }
[[model.effort]]
effort = "max"
rank = 2
floor = 2
use = "prohibited: fixture ceiling"
[[model]]
id = "clay"
family = "kiln-lab"
[[model.effort]]
effort = "medium"
rank = 2
floor = 1
seat_rank = { kiln = 1 }
[[model.effort]]
effort = "low"
rank = 1
floor = 1
''',
    "profiles.toml": '''
[[profile]]
id = "compose"
purpose = "Compose a fixture document"
provider = "paper"
model = "inkstone"
backend_model = "paper/inkstone"
effort = "low"
stability = "stable"
backends = ["desk"]
[[profile.variant]]
id = "deep"
provider = "paper"
model = "inkstone"
backend_model = "paper/inkstone-deep"
effort = "high"
stability = "stable"
backends = ["desk"]
[[profile.variant]]
id = "remote"
provider = "paper"
model = "inkstone"
backend_model = "paper/inkstone-deep"
effort = "high"
stability = "stable"
backends = ["bench"]
default_for_backend = true
[[profile.variant]]
id = "trial"
provider = "kiln"
model = "clay"
effort = "low"
stability = "experimental"
backends = ["desk"]
[[profile.variant]]
id = "peer"
provider = "kiln"
model = "clay"
effort = "medium"
stability = "stable"
backends = ["desk"]
[[profile]]
id = "sample"
purpose = "Sample a fixture document"
provider = "kiln"
model = "clay"
effort = "low"
stability = "probationary"
backends = ["bench"]
''',
    "delegation.toml": '''
[[backend]]
id = "desk"
status = "verified"
providers = ["paper", "kiln"]
supported_efforts = ["low", "medium", "high"]
[[backend]]
id = "bench"
status = "verified"
providers = ["paper", "kiln"]
supported_efforts = ["low", "medium", "high"]
[[pool]]
provider = "paper"
serves = ["inkstone"]
[[pool]]
provider = "kiln"
serves = ["clay"]
''',
}


class RoutesViewTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        (root / "routing").mkdir()
        for name, body in FIXTURE.items():
            (root / "routing" / name).write_text(body)
        return root

    def assert_resolution_inventory(self, root):
        profiles = tomllib.loads((root / "routing/profiles.toml").read_text())["profile"]
        backends = tomllib.loads((root / "routing/delegation.toml").read_text())["backend"]
        seats = seats_view(root)["seats"]
        expected = {}
        for profile in profiles:
            for variant in [None, *(row["id"] for row in profile.get("variant", []))]:
                for backend in backends:
                    try:
                        route = resolve(root, profile["id"], backend["id"], variant_id=variant)
                    except RouteRefusal as error:
                        self.assertIn(error.kind, {"stability", "unsupported-backend", "pool"})
                        continue
                    coordinate = (profile["id"], variant, backend["id"])
                    default = next(seat["default"] for seat in seats
                                   if seat["profile"] == profile["id"] and seat["backend"] == backend["id"]
                                   and (seat["default"] if variant is None else seat["variant"] == variant))
                    expected[coordinate] = {
                        "profile": profile["id"], "variant": variant, "backend": backend["id"],
                        **{key: route[key] for key in ("model", "effort", "provider", "stability")},
                        "default": default,
                    }
        answer = routes_view(root)
        self.assertEqual(answer["schema"], "agent-routing-routes/1")
        self.assertEqual(answer["route_version"], route_version(root))
        actual = {(row["profile"], row["variant"], row["backend"]): row for row in answer["routes"]}
        self.assertEqual(actual, expected, "listing must equal every successful plain resolve coordinate")
        self.assertEqual(len(answer["routes"]), len(actual), "duplicate coordinates")
        self.assertEqual(list(actual), sorted(actual, key=lambda key: (key[0], key[1] or "", key[2])))
        models = tomllib.loads((root / "routing/models.toml").read_text())["model"]
        prohibited = [{"model": model["id"], "effort": tier["effort"], "reason": tier["use"]}
                      for model in models for tier in model.get("effort", [])
                      if str(tier.get("use", "")).startswith("prohibited")]
        self.assertEqual(answer["prohibited"], sorted(prohibited, key=lambda row: (row["model"], row["effort"])))

    def test_listing_equals_every_plain_resolution(self):
        """Reject missing variants/defaults, extra opt-in routes, and mismatched tuples."""
        self.assert_resolution_inventory(self.fixture_root())

    def test_frozen_roster_listing_equals_every_plain_resolution(self):
        self.assert_resolution_inventory(ROOT)

    def test_filters_preserve_the_matching_routes_and_all_prohibitions(self):
        root = self.fixture_root()
        answer = routes_view(root)
        for row in answer["routes"]:
            for filters in ({"profile_id": row["profile"]}, {"backend": row["backend"]},
                            {"profile_id": row["profile"], "backend": row["backend"]}):
                filtered = routes_view(root, **filters)
                self.assertEqual(filtered, {**answer, "routes": [route for route in answer["routes"]
                    if all(route["profile" if key == "profile_id" else key] == value
                           for key, value in filters.items())]})
        for filters in ({"profile_id": "absent"}, {"backend": "absent"}):
            self.assertEqual(routes_view(root, **filters), {**answer, "routes": []})

    def test_cli_requires_json_and_emits_the_filtered_contract(self):
        root = self.fixture_root()
        for name in ("bin", "lib"):
            shutil.copytree(REPOSITORY / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
        command = [root / "bin/agent-routing", "routes"]
        refused = subprocess.run(command, capture_output=True, text=True, timeout=5)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(refused.stdout, "")
        self.assertIn("--json", refused.stderr)
        answer = routes_view(root)
        row = answer["routes"][0]
        for flags, expected in (
            ([], answer),
            (["--backend", row["backend"]], routes_view(root, backend=row["backend"])),
            (["--profile", row["profile"]], routes_view(root, profile_id=row["profile"])),
            (["--profile", row["profile"], "--backend", row["backend"]],
             routes_view(root, profile_id=row["profile"], backend=row["backend"])),
            (["--profile", "absent"], {**answer, "routes": []}),
        ):
            result = subprocess.run([*command, "--json", *flags], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(json.loads(result.stdout), expected)


if __name__ == "__main__":
    unittest.main()
