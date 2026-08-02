import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from routing_profiles import resolve, validation_problems


class RoutingProfilesTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        shutil.copytree(ROOT / "routing", root / "routing")
        return root

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
            resolve(ROOT, "implement", "opencode", variant_id="opencode-go-trial")

    def test_experimental_base_profile_fails_closed(self):
        """A whole profile can be experimental, not only a variant of a stable one."""
        with self.assertRaisesRegex(ValueError, "--allow-experimental"):
            resolve(ROOT, "generate", "pi")
        route = resolve(ROOT, "generate", "pi", allow_experimental=True)
        self.assertEqual(route["stability"], "experimental")

    def test_backend_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "does not support backend"):
            resolve(ROOT, "design", "codex")

    def test_stable_variant_does_not_need_experimental_opt_in(self):
        route = resolve(ROOT, "review", "codex", variant_id="high-stakes")
        self.assertEqual(route["profile"], "review:high-stakes")
        self.assertEqual(route["stability"], "stable")

    def test_interactive_parent_route_is_pi_only(self):
        route = resolve(ROOT, "interactive", "pi")
        self.assertEqual(route["profile"], "interactive")
        with self.assertRaisesRegex(ValueError, "does not support backend"):
            resolve(ROOT, "interactive", "codex")

    def test_experimental_model_cannot_be_labeled_stable(self):
        root = self.fixture_root()
        path = root / "routing" / "profiles.toml"
        text = path.read_text().replace(
            'model = "deepseek-v4-flash"\neffort = "max"\nstability = "experimental"',
            'model = "deepseek-v4-flash"\neffort = "max"\nstability = "stable"',
        )
        path.write_text(text)
        self.assertTrue(any("experimental model" in problem for problem in validation_problems(root)))

    def test_explicit_only_tier_cannot_back_a_profile(self):
        root = self.fixture_root()
        path = root / "routing" / "profiles.toml"
        path.write_text(path.read_text() + '''

[[profile]]
id = "bad-explicit"
purpose = "fixture"
provider = "anthropic"
model = "opus-5"
effort = "high"
stability = "stable"
backends = ["claude"]
''')
        self.assertTrue(any("requires an explicit model request" in problem for problem in validation_problems(root)))

    def test_unknown_model_and_unverified_backend_are_rejected(self):
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        profiles.write_text(profiles.read_text().replace('model = "gpt-5.6-luna"', 'model = "missing-model"', 1))
        delegation = root / "routing" / "delegation.toml"
        delegation.write_text(delegation.read_text().replace('id = "codex"\nstatus = "verified"', 'id = "codex"\nstatus = "unprobed"', 1))
        problems = validation_problems(root)
        self.assertTrue(any("unknown model" in problem for problem in problems))
        self.assertTrue(any("backend 'codex' is not verified" in problem for problem in problems))

    def test_unknown_status_vocabulary_is_rejected(self):
        root = self.fixture_root()
        models = root / "routing" / "models.toml"
        models.write_text(models.read_text().replace('status = "explicit-only"', 'status = "explicit_only"', 1))
        self.assertTrue(any("unknown status" in problem for problem in validation_problems(root)))

    def test_resolve_cli_keeps_errors_off_stdout(self):
        command = ROOT / "bin" / "resolve-route"
        unknown = subprocess.run(
            [command, "missing", "--backend", "codex", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(unknown.returncode, 1)
        self.assertEqual(unknown.stdout, "")
        self.assertIn("unknown profile", unknown.stderr)
        missing_backend = subprocess.run([command, "implement", "--json"], capture_output=True, text=True)
        self.assertEqual(missing_backend.returncode, 2)
        self.assertEqual(missing_backend.stdout, "")

    def test_check_distinguishes_explicit_tiers_and_status_only_models(self):
        command = ROOT / "bin" / "routing-check"
        explicit = subprocess.run([command, "opus-5", "high"], capture_output=True, text=True)
        self.assertEqual(explicit.returncode, 0)
        self.assertIn("explicit-only", explicit.stdout)
        restricted = subprocess.run([command, "sonnet-5", "low"], capture_output=True, text=True)
        self.assertEqual(restricted.returncode, 0)
        self.assertIn("restricted", restricted.stdout)

    def test_route_version_covers_every_routing_manifest(self):
        root = self.fixture_root()
        versions = [resolve(root, "implement", "codex")["route_version"]]
        for filename in ("models.toml", "profiles.toml", "delegation.toml"):
            path = root / "routing" / filename
            original = path.read_text()
            path.write_text(original + "\n")
            versions.append(resolve(root, "implement", "codex")["route_version"])
            path.write_text(original)
        self.assertEqual(len(set(versions)), 4)


if __name__ == "__main__":
    unittest.main()
