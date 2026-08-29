import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from routing_profiles import RouteRefusal, pool_problems, resolve, validation_problems


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

    def test_implement_takes_the_stable_workhorse_at_max(self):
        """Luna holds the seat Terra held before its price reset, so the
        primary is the measured implementer rather than a trial variant."""
        route = resolve(ROOT, "implement", "codex")
        self.assertEqual(route["model"], "gpt-5.6-luna")
        self.assertEqual(route["effort"], "max")
        self.assertEqual(route["stability"], "stable")

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
        # Prose for a person, then the payload alone on the last line for the
        # caller that has to classify the refusal.
        payload = json.loads(unknown.stderr.splitlines()[-1])
        self.assertEqual(payload["schema"], "agent-routing-refusal/1")
        self.assertEqual(payload["kind"], "unknown-profile")
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

    def cross_pool_root(self):
        """A fixture whose review profile routes Sol through the small plan."""
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        start = text.index('id = "review"')
        head, tail = text[:start], text[start:]
        tail = tail.replace(
            '''  id = "goat"
  provider = "commandcode"
  model = "gpt-5.6-luna"
  effort = "max"''',
            '''  id = "goat-sol"
  provider = "commandcode"
  model = "gpt-5.6-sol"
  effort = "high"''',
            1,
        )
        profiles.write_text(head + tail)
        return root

    def test_a_pool_refusal_names_the_subscription_that_pays(self):
        root = self.cross_pool_root()
        with self.assertRaises(RouteRefusal) as caught:
            resolve(root, "review", "pi", variant_id="goat-sol")
        refusal = caught.exception
        self.assertEqual(refusal.kind, "pool")
        payload = refusal.payload()
        self.assertEqual(payload["model"], "gpt-5.6-sol")
        self.assertEqual(payload["override"], "--allow-cross-pool")
        self.assertIn("openai-codex", payload["alternative"])

    def test_crossing_a_pool_is_opt_in_and_recorded(self):
        root = self.cross_pool_root()
        route = resolve(root, "review", "pi", variant_id="goat-sol", allow_cross_pool=True)
        self.assertEqual(route["model"], "gpt-5.6-sol")
        self.assertIn("cross_pool", route)

    def test_one_pool_violation_does_not_block_an_unrelated_route(self):
        """A pool pairing is a property of one route. Blocking every other
        resolution would make a single bad variant an outage."""
        root = self.cross_pool_root()
        self.assertEqual(resolve(root, "review", "codex")["model"], "gpt-5.6-luna")
        self.assertEqual(len(pool_problems(root)), 1)

    def test_a_refusal_carries_its_kind(self):
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "nosuch", "pi")
        self.assertEqual(caught.exception.kind, "unknown-profile")
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "generate", "pi")
        self.assertEqual(caught.exception.kind, "stability")
        self.assertEqual(caught.exception.payload()["override"], "--allow-experimental")
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "design", "codex")
        self.assertEqual(caught.exception.kind, "unsupported-backend")



    def test_a_manifest_that_cannot_be_read_still_answers_with_a_payload(self):
        """A refusal raised before a route exists is still a refusal a caller
        must classify, so an unreadable manifest answers in the same shape."""
        root = self.fixture_root()
        (root / "bin").mkdir()
        shutil.copy(ROOT / "bin" / "resolve-route", root / "bin" / "resolve-route")
        shutil.copytree(ROOT / "lib", root / "lib")
        models = root / "routing" / "models.toml"
        models.write_text(models.read_text() + "\nnot toml [[[\n")
        completed = subprocess.run(
            [root / "bin" / "resolve-route", "implement", "--backend", "codex", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        payload = json.loads(completed.stderr.strip().splitlines()[-1])
        self.assertEqual(payload["schema"], "agent-routing-refusal/1")
        self.assertEqual(payload["kind"], "manifest-invalid")


if __name__ == "__main__":
    unittest.main()
