import json
import os
import pathlib
import subprocess
import sys
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from routing_profiles import resolve, route_version, seats_view

class SeatViewTest(unittest.TestCase):
    def test_bindings_preserve_each_declared_backend_and_variant(self):
        profiles = tomllib.loads((ROOT / "routing/profiles.toml").read_text())["profile"]
        expected = {(p["id"], None if route is p else route["id"], backend)
                    for p in profiles for route in (p, *p.get("variant", [])) for backend in route["backends"]}
        view = seats_view(ROOT)
        self.assertEqual({(s["profile"], s["variant"], s["backend"]) for s in view["seats"]}, expected)
        self.assertEqual(len(view["seats"]), len(expected))
        self.assertEqual(view["head_default"], resolve(ROOT, "plan", "claude"))
        self.assertIsNone(view["head_default_refusal"])
        for seat in view["seats"]:
            with self.subTest(seat=seat):
                route = resolve(ROOT, seat["profile"], seat["backend"], variant_id=seat["variant"], allow_experimental=True)
                for key in ("model", "effort", "provider", "stability", "route_version"):
                    self.assertEqual(seat[key], route[key])
                if seat["default"]:
                    self.assertEqual(route, resolve(ROOT, seat["profile"], seat["backend"], allow_experimental=True))

    def test_cli_never_treats_ambient_model_as_the_actual_head(self):
        result = subprocess.run([ROOT / "bin/agent-routing", "seats", "--json"], capture_output=True, text=True,
                                env=dict(os.environ, ARC_MODEL="fixture-impostor#max"))
        self.assertEqual(result.returncode, 0, result.stderr)
        view = json.loads(result.stdout)
        self.assertEqual(view["schema"], "agent-routing-seats/1")
        self.assertEqual(view["actual_head"], {"status": "unobserved"})
        self.assertEqual(view["route_version"], route_version(ROOT))
