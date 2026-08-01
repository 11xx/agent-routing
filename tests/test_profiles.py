import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from routing_profiles import resolve, validation_problems


class RoutingProfilesTest(unittest.TestCase):
    def test_manifest_is_valid(self):
        self.assertEqual(validation_problems(ROOT), [])

    def test_stable_route_resolves_for_supported_backend(self):
        route = resolve(ROOT, "implement", "codex")
        self.assertEqual(route["profile"], "implement")
        self.assertEqual(route["backend"], "codex")
        self.assertEqual(route["stability"], "stable")
        self.assertTrue(route["route_version"])

    def test_experimental_variant_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "--allow-experimental"):
            resolve(ROOT, "implement", "pi", variant_id="deepseek")

    def test_backend_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "does not support backend"):
            resolve(ROOT, "design", "codex")


if __name__ == "__main__":
    unittest.main()
