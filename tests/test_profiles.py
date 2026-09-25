import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from routing_profiles import (
    RouteRefusal,
    pool_problems,
    resolve,
    validate_selection,
    validation_problems,
)


class RoutingProfilesTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        shutil.copytree(ROOT / "routing", root / "routing")
        return root

    def add_generator_model(self, root):
        """Add a generator-only roster row; no shipped model holds that role."""
        models = root / "routing" / "models.toml"
        models.write_text(models.read_text() + '''
[[model]]
id = "fixture-generator"
family = "fixture"
role = "steered generator for tests only"
  [[model.effort]]
  effort = "max"
  use = "fixture tier"
''')
        return "fixture-generator"

    def add_implement_variant(self, root, variant):
        """Append a variant to the implement profile of a fixture manifest."""
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        anchor = '[[profile]]\nid = "generate"'
        self.assertIn(anchor, text)
        profiles.write_text(text.replace(anchor, variant + "\n" + anchor, 1))

    def direct_selection(self, root=ROOT, **overrides):
        values = {
            "profile_id": "implement",
            "backend": "codex",
            "model": "gpt-6-luna",
            "effort": "max",
            "provider": "openai-codex",
            "reason": "operator directed",
            "allow_experimental": True,
        }
        values.update(overrides)
        return validate_selection(root, **values)

    def test_manifest_is_valid(self):
        self.assertEqual(validation_problems(ROOT), [])

    def test_generator_only_variant_requires_role_exception(self):
        root = self.fixture_root()
        self.add_generator_model(root)
        self.add_implement_variant(root, '''  [[profile.variant]]
  id = "generator-without-exception"
  provider = "deepseek"
  model = "fixture-generator"
  effort = "max"
  stability = "experimental"
  backends = ["pi"]
''')

        problems = validation_problems(root)
        self.assertTrue(
            any("generator-only" in problem and "generator-without-exception" in problem for problem in problems),
            problems,
        )

    def test_role_exception_reason_must_not_be_blank(self):
        root = self.fixture_root()
        self.add_generator_model(root)
        self.add_implement_variant(root, '''  [[profile.variant]]
  id = "generator-with-blank-exception"
  provider = "deepseek"
  model = "fixture-generator"
  effort = "max"
  stability = "experimental"
  backends = ["pi"]
  role_exception = "  "
''')

        problems = validation_problems(root)
        self.assertTrue(
            any("generator-with-blank-exception: role_exception must be a nonblank reason" in problem for problem in problems),
            problems,
        )

    def test_computer_use_is_explicit_and_has_comparison_tiers(self):
        for backend in ("codex", "pi"):
            for variant, effort in ((None, "low"), ("medium", "medium"),
                                    ("high", "high"), ("xhigh", "xhigh")):
                with self.assertRaises(RouteRefusal):
                    resolve(ROOT, "computer-use", backend, variant_id=variant)
                route = resolve(ROOT, "computer-use", backend, variant_id=variant,
                                allow_experimental=True)
                self.assertEqual((route["model"], route["effort"]), ("gpt-6-sol", effort))

    def test_sol_max_is_prohibited_while_computer_use_tiers_remain_available(self):
        for effort in ("low", "medium", "high", "xhigh"):
            self.direct_selection(profile_id="computer-use", model="gpt-6-sol",
                                  effort=effort)
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(profile_id="computer-use", model="gpt-6-sol",
                                  effort="max")
        self.assertEqual(caught.exception.kind, "prohibited")

    def test_opus_computer_use_requires_explicit_claude_selection(self):
        with self.assertRaises(RouteRefusal):
            resolve(ROOT, "computer-use", "claude", allow_experimental=True)
        with self.assertRaises(RouteRefusal):
            resolve(ROOT, "computer-use", "claude", variant_id="opus")
        route = resolve(ROOT, "computer-use", "claude", variant_id="opus",
                        allow_experimental=True)
        self.assertEqual((route["model"], route["effort"]),
                         ("claude-opus-5-5", "medium"))
        for effort in ("low", "medium", "high", "xhigh", "max"):
            selection = self.direct_selection(
                profile_id="computer-use", backend="claude", model="opus-5.5",
                effort=effort, provider="anthropic",
            )
            self.assertEqual(selection["backend_model"], "claude-opus-5-5")
            self.assertEqual(selection["effort"], effort)
            self.assertEqual(selection["selection_kind"], "operator-directed")

    def test_stable_route_resolves_for_supported_backend(self):
        route = resolve(ROOT, "implement", "codex")
        self.assertEqual(route["profile"], "implement")
        self.assertEqual(route["backend"], "codex")
        self.assertEqual(route["stability"], "stable")
        self.assertTrue(route["route_version"])

    def test_claude_opus_variant_is_a_stable_first_party_review_route(self):
        route = resolve(ROOT, "review", "claude", variant_id="opus")
        self.assertEqual(route["profile"], "review:opus")
        self.assertEqual(route["backend"], "claude")
        self.assertEqual(route["provider"], "anthropic")
        self.assertEqual(route["model"], "claude-opus-5-5")
        self.assertEqual(route["effort"], "medium")
        self.assertEqual(route["stability"], "stable")

    def test_claude_backend_defaults_to_opus_medium_for_work_and_review(self):
        for profile in ("implement", "execute", "review"):
            route = resolve(ROOT, profile, "claude")
            self.assertEqual(route["profile"], f"{profile}:opus")
            self.assertEqual(route["backend"], "claude")
            self.assertEqual(route["provider"], "anthropic")
            self.assertEqual(route["model"], "claude-opus-5-5")
            self.assertEqual(route["effort"], "medium")
            self.assertEqual(route["stability"], "stable")

    def test_only_one_variant_can_default_for_each_backend(self):
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        anchor = text.index('id = "implement"')
        insert = text.index("\n\n", anchor)
        duplicate = '''
  [[profile.variant]]
  id = "second-claude-default"
  provider = "anthropic"
  model = "opus-5.5"
  backend_model = "claude-opus-5-5"
  effort = "medium"
  stability = "stable"
  backends = ["claude"]
  default_for_backend = true
'''
        profiles.write_text(text[:insert] + "\n" + duplicate + text[insert:])

        self.assertTrue(
            any("already defaults" in problem for problem in validation_problems(root))
        )

    def test_a_default_the_primary_route_would_shadow_is_refused(self):
        """A default is reachable only where the primary excludes the backend.

        The resolver consults a backend default only when the primary route
        does not serve that backend, so one naming a backend the primary
        already serves can never be selected. Left unchecked it reads as an
        effective override while the primary keeps answering.
        """
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        anchor = text.index('id = "implement"')
        insert = text.index("\n\n", anchor)
        shadowed = '''
  [[profile.variant]]
  id = "shadowed"
  provider = "openai-codex"
  model = "gpt-5.6-luna"
  effort = "max"
  stability = "stable"
  backends = ["codex"]
  default_for_backend = true
'''
        profiles.write_text(text[:insert] + "\n" + shadowed + text[insert:])

        self.assertTrue(
            any("is unreachable" in problem for problem in validation_problems(root))
        )

    def test_an_unknown_route_key_is_refused(self):
        """A misspelled key is ignored by every reader, so it must be refused.

        `default_for_backend` written at profile level, or spelled
        `default_for_backends` on a variant, would otherwise leave the route
        resolving exactly as it did before the edit.
        """
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        anchor = text.index('id = "implement"')
        insert = text.index("\n", anchor)
        profiles.write_text(
            text[:insert] + "\ndefault_for_backend = true" + text[insert:]
        )

        self.assertTrue(
            any("unknown key" in problem for problem in validation_problems(root))
        )

    def test_cli_exposes_the_named_claude_review_route(self):
        command = ROOT / "bin" / "agent-routing"
        completed = subprocess.run(
            [command, "resolve", "review", "--backend", "claude", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        route = json.loads(completed.stdout)
        self.assertEqual(route["profile"], "review:opus")
        self.assertEqual(route["backend"], "claude")
        self.assertEqual(route["model"], "claude-opus-5-5")
        self.assertEqual(route["effort"], "medium")
        self.assertEqual(route["stability"], "stable")

    def test_direct_selection_refuses_a_prohibited_tier(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                profile_id="implement",
                backend="claude",
                model="opus-5",
                effort="max",
                provider="anthropic",
            )
        self.assertEqual(caught.exception.kind, "prohibited")
        self.assertIn("prohibited", caught.exception.message)

    def test_direct_selection_refuses_unknown_pool_membership_by_fact(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                profile_id="generate",
                backend="pi",
                model="deepseek-flash",
                effort="max",
                provider="deepseek",
            )
        refusal = caught.exception
        self.assertEqual(refusal.kind, "unknown-pool-membership")
        self.assertIn("pool membership", refusal.payload()["missing_fact"])
        self.assertNotIn("override", refusal.payload())

    def test_direct_selection_requires_cross_pool_opt_in(self):
        values = {
            "profile_id": "review",
            "backend": "pi",
            "model": "gpt-6-sol",
            "effort": "high",
            "provider": "opencode-go",
        }
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(**values)
        self.assertEqual(caught.exception.kind, "pool")
        self.assertEqual(caught.exception.payload()["override"], "--allow-cross-pool")
        route = self.direct_selection(allow_cross_pool=True, **values)
        self.assertEqual(route["cross_pool"], "OpenCode Go, an optional flat subscription")

    def test_direct_selection_requires_experimental_opt_in_even_for_rostered_model(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(allow_experimental=False)
        self.assertEqual(caught.exception.kind, "stability")
        self.assertEqual(caught.exception.payload()["stability"], "experimental")

    def test_direct_selection_accepts_tuple_with_operator_witness(self):
        route = self.direct_selection(
            profile_id="plan",
            backend="codex",
            model="gpt-6-astra",
            effort="low",
            provider="openai-codex",
        )
        self.assertEqual(route["selection_kind"], "operator-directed")
        self.assertEqual(route["base_profile"], "plan")
        self.assertEqual(route["canonical_model"], "gpt-6-astra")
        self.assertEqual(route["backend_model"], "gpt-6-astra")
        self.assertEqual(route["stability"], "experimental")
        self.assertFalse(route["rostered"])
        self.assertTrue(route["route_version"])

    def test_direct_selection_accepts_model_without_a_profile_variant(self):
        route = self.direct_selection(
            profile_id="implement",
            backend="claude",
            model="fable-5.1",
            effort="high",
            provider="anthropic",
        )
        self.assertEqual(route["selection_kind"], "operator-directed")
        self.assertEqual(route["model"], "fable-5.1")
        self.assertEqual(route["backend_model"], "claude-fable-5-1")
        self.assertEqual(route["stability"], "experimental")

    def test_cross_pool_opt_in_cannot_waive_unknown_backend_model_support(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                profile_id="implement",
                backend="claude",
                model="gpt-6-astra",
                effort="medium",
                provider="anthropic",
                allow_cross_pool=True,
            )
        refusal = caught.exception
        self.assertEqual(refusal.kind, "unsupported-model")
        self.assertIn("backend model support", refusal.payload()["missing_fact"])

    def test_direct_selection_applies_generator_role_restriction(self):
        root = self.fixture_root()
        model = self.add_generator_model(root)
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                root,
                profile_id="implement",
                backend="pi",
                model=model,
                effort="max",
                provider="deepseek",
            )
        self.assertEqual(caught.exception.kind, "model-role")

    def test_direct_selection_applies_lead_role_restriction(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                profile_id="plan",
                backend="codex",
                model="gpt-5.6-luna",
                effort="max",
                provider="openai-codex",
            )
        self.assertEqual(caught.exception.kind, "model-role")

    def test_validate_cli_emits_operator_directed_json(self):
        command = ROOT / "bin" / "agent-routing"
        completed = subprocess.run(
            [
                command,
                "validate",
                "--profile",
                "plan",
                "--backend",
                "codex",
                "--model",
                "gpt-6-astra",
                "--effort",
                "low",
                "--provider",
                "openai-codex",
                "--reason",
                "operator directed",
                "--allow-experimental",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        selection = json.loads(completed.stdout)
        self.assertEqual(selection["selection_kind"], "operator-directed")
        self.assertEqual(selection["base_profile"], "plan")

    def test_validate_cli_keeps_refusal_payload_on_stderr(self):
        command = ROOT / "bin" / "agent-routing"
        completed = subprocess.run(
            [
                command,
                "validate",
                "--profile",
                "implement",
                "--backend",
                "claude",
                "--model",
                "opus-5",
                "--effort",
                "max",
                "--provider",
                "anthropic",
                "--reason",
                "operator directed",
                "--allow-experimental",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        payload = json.loads(completed.stderr.splitlines()[-1])
        self.assertEqual(payload["schema"], "agent-routing-refusal/1")
        self.assertEqual(payload["kind"], "prohibited")

    def test_mimo_rows_are_operator_directed_trials(self):
        """Neither MiMo row carries a profile, so the path that has to work is
        a validated operator-directed selection on the Go pool — under the
        vendor id and under the operator's shorthand alike."""
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                profile_id="implement",
                backend="pi",
                model="mimo-v2.6-flash",
                effort="high",
                provider="opencode-go",
                allow_experimental=False,
            )
        self.assertEqual(caught.exception.kind, "stability")

        for model, canonical in (
            ("mimo-v2.6-flash", "mimo-v2.6-flash"),
            ("mimo-2.6-flash", "mimo-v2.6-flash"),
            ("mimo-v2.6-pro", "mimo-v2.6-pro"),
            ("mimo-2.6-pro", "mimo-v2.6-pro"),
        ):
            with self.subTest(model=model):
                selection = self.direct_selection(
                    profile_id="implement",
                    backend="pi",
                    model=model,
                    effort="high",
                    provider="opencode-go",
                )
                self.assertEqual(selection["canonical_model"], canonical)
                # The backend identity is what a caller hands pi, so prose
                # punctuation around it in the flag string must not travel.
                self.assertEqual(selection["backend_model"], canonical)
                self.assertEqual(selection["stability"], "experimental")
                self.assertEqual(selection["selection_kind"], "operator-directed")

    def test_check_resolves_a_roster_alias_to_its_canonical_id(self):
        for argument, expected in (
            ("mimo-2.6-flash", "mimo-v2.6-flash"),
            ("mimo-v2.6-pro", "mimo-v2.6-pro"),
        ):
            with self.subTest(argument=argument):
                completed = subprocess.run(
                    [ROOT / "bin" / "routing-check", argument, "high"],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn(f"not prohibited: {expected}", completed.stdout)

    def test_experimental_variant_fails_closed(self):
        """A variant carries its own stability, independent of its profile's.

        No shipped profile declares an experimental variant, so this builds one
        rather than pinning the test to whichever route happens to be a trial.
        """
        root = self.fixture_root()
        manifest = root / "routing" / "profiles.toml"
        variant = (
            '\n  [[profile.variant]]\n'
            '  id = "trial"\n'
            '  provider = "openai-codex"\n'
            '  model = "gpt-6-luna"\n'
            '  effort = "max"\n'
            '  stability = "experimental"\n'
            '  backends = ["codex"]\n'
        )
        text = manifest.read_text()
        anchor = text.index('id = "implement"')
        insert = text.index("\n\n", anchor)
        manifest.write_text(text[:insert] + "\n" + variant + text[insert:])
        with self.assertRaisesRegex(ValueError, "--allow-experimental"):
            resolve(root, "implement", "codex", variant_id="trial")
        route = resolve(root, "implement", "codex", variant_id="trial", allow_experimental=True)
        self.assertEqual(route["stability"], "experimental")

    def test_implement_takes_the_stable_workhorse_at_max(self):
        """The primary is the workhorse tier, not a trial variant."""
        route = resolve(ROOT, "implement", "codex")
        self.assertEqual(route["model"], "gpt-6-luna")
        self.assertEqual(route["effort"], "max")
        self.assertEqual(route["stability"], "stable")

    def experimental_generate_root(self):
        """A fixture whose whole generate profile is experimental."""
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        start = text.index('id = "generate"')
        head, tail = text[:start], text[start:]
        profiles.write_text(head + tail.replace('stability = "stable"', 'stability = "experimental"', 1))
        return root

    def test_experimental_base_profile_fails_closed(self):
        """A whole profile can be experimental, not only a variant of a stable one."""
        root = self.experimental_generate_root()
        with self.assertRaisesRegex(ValueError, "--allow-experimental"):
            resolve(root, "generate", "pi")
        route = resolve(root, "generate", "pi", allow_experimental=True)
        self.assertEqual(route["stability"], "experimental")

    def test_generate_runs_on_the_go_pool(self):
        route = resolve(ROOT, "generate", "pi")
        self.assertEqual(route["provider"], "opencode-go")
        self.assertEqual(route["model"], "deepseek-v4.1-flash")
        self.assertEqual(route["stability"], "stable")

    def test_backend_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "does not support backend"):
            resolve(ROOT, "design", "codex")

    def test_stable_variant_does_not_need_experimental_opt_in(self):
        route = resolve(ROOT, "review", "codex", variant_id="high-stakes")
        self.assertEqual(route["profile"], "review:high-stakes")
        self.assertEqual(route["stability"], "stable")

    def test_review_default_and_named_variants(self):
        route = resolve(ROOT, "review", "codex")
        self.assertEqual(route["profile"], "review")
        self.assertEqual(route["provider"], "openai-codex")
        self.assertEqual((route["model"], route["effort"]), ("gpt-6-astra", "medium"))
        self.assertEqual(route["stability"], "stable")

        fast = resolve(ROOT, "review", "codex", variant_id="fast")
        self.assertEqual((fast["model"], fast["effort"]), ("gpt-6-sol", "high"))
        high_stakes = resolve(ROOT, "review", "codex", variant_id="high-stakes")
        self.assertEqual((high_stakes["model"], high_stakes["effort"]), ("gpt-6-astra", "xhigh"))

    def test_interactive_parent_route_is_pi_only(self):
        route = resolve(ROOT, "interactive", "pi")
        self.assertEqual(route["profile"], "interactive")
        with self.assertRaisesRegex(ValueError, "does not support backend"):
            resolve(ROOT, "interactive", "codex")

    def test_experimental_model_cannot_be_labeled_stable(self):
        root = self.fixture_root()
        models = root / "routing" / "models.toml"
        models.write_text(models.read_text().replace(
            'id = "gpt-6-luna"\nfamily = "openai"\n',
            'id = "gpt-6-luna"\nfamily = "openai"\nstatus = "experimental"\n',
            1,
        ))
        self.assertTrue(any("experimental model" in problem for problem in validation_problems(root)))

    def test_explicit_only_tier_cannot_back_a_profile(self):
        root = self.fixture_root()
        path = root / "routing" / "profiles.toml"
        path.write_text(path.read_text() + '''

[[profile]]
id = "bad-explicit"
purpose = "fixture"
provider = "anthropic"
model = "opus-5.5"
effort = "high"
stability = "stable"
backends = ["claude"]
''')
        self.assertTrue(any("requires an explicit model request" in problem for problem in validation_problems(root)))

    def test_unknown_model_and_unverified_backend_are_rejected(self):
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        profiles.write_text(profiles.read_text().replace('model = "gpt-6-luna"', 'model = "missing-model"', 1))
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
        explicit = subprocess.run([command, "opus-5.5", "high"], capture_output=True, text=True)
        self.assertEqual(explicit.returncode, 0)
        self.assertIn("explicit-only", explicit.stdout)
        restricted = subprocess.run([command, "sonnet-5", "low"], capture_output=True, text=True)
        self.assertEqual(restricted.returncode, 0)
        self.assertIn("restricted", restricted.stdout)
        for model in ("opus-5", "opus-4.8"):
            with self.subTest(model=model):
                superseded = subprocess.run([command, model, "medium"], capture_output=True, text=True)
                self.assertEqual(superseded.returncode, 0)
                self.assertTrue(superseded.stdout.startswith("superseded: "), superseded.stdout)

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
        """A fixture whose review profile routes Sol through the Go plan."""
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        anchor = '[[profile]]\nid = "design"'
        self.assertIn(anchor, text)
        variant = '''  [[profile.variant]]
  id = "go-sol"
  provider = "opencode-go"
  model = "gpt-6-sol"
  effort = "high"
  stability = "stable"
  backends = ["pi"]

'''
        profiles.write_text(text.replace(anchor, variant + anchor, 1))
        return root

    def test_a_pool_refusal_names_the_subscription_that_pays(self):
        root = self.cross_pool_root()
        with self.assertRaises(RouteRefusal) as caught:
            resolve(root, "review", "pi", variant_id="go-sol")
        refusal = caught.exception
        self.assertEqual(refusal.kind, "pool")
        payload = refusal.payload()
        self.assertEqual(payload["model"], "gpt-6-sol")
        self.assertEqual(payload["override"], "--allow-cross-pool")
        self.assertIn("openai-codex", payload["alternative"])

    def test_crossing_a_pool_is_opt_in_and_recorded(self):
        root = self.cross_pool_root()
        route = resolve(root, "review", "pi", variant_id="go-sol", allow_cross_pool=True)
        self.assertEqual(route["model"], "gpt-6-sol")
        self.assertIn("cross_pool", route)

    def test_one_pool_violation_does_not_block_an_unrelated_route(self):
        """A pool pairing is a property of one route. Blocking every other
        resolution would make a single bad variant an outage."""
        root = self.cross_pool_root()
        self.assertEqual(resolve(root, "review", "codex")["model"], "gpt-6-astra")
        self.assertEqual(len(pool_problems(root)), 1)

    def test_a_refusal_carries_its_kind(self):
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "nosuch", "pi")
        self.assertEqual(caught.exception.kind, "unknown-profile")
        with self.assertRaises(RouteRefusal) as caught:
            resolve(self.experimental_generate_root(), "generate", "pi")
        self.assertEqual(caught.exception.kind, "stability")
        self.assertEqual(caught.exception.payload()["override"], "--allow-experimental")
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "design", "codex")
        self.assertEqual(caught.exception.kind, "unsupported-backend")

    def test_pi_defaults_to_deepseek_on_the_go_pool(self):
        for profile in ("extract", "explore", "implement", "plan", "execute", "review"):
            route = resolve(ROOT, profile, "pi")
            self.assertEqual(route["profile"], f"{profile}:deepseek-go")
            self.assertEqual(route["provider"], "opencode-go")
            self.assertEqual(route["model"], "deepseek-v4.1-flash")
            self.assertEqual(route["effort"], "max")
            self.assertEqual(route["stability"], "stable")
        interactive = resolve(ROOT, "interactive", "pi")
        self.assertEqual((interactive["provider"], interactive["model"]), ("opencode-go", "deepseek-v4.1-flash"))

    def test_resolve_json_reports_declared_role_exception(self):
        root = self.fixture_root()
        for directory in ("bin", "lib"):
            shutil.copytree(ROOT / directory, root / directory)
        self.add_generator_model(root)
        reason = "operator-directed defect generation, reviewed by a lead"
        self.add_implement_variant(root, f'''  [[profile.variant]]
  id = "defects"
  provider = "deepseek"
  model = "fixture-generator"
  effort = "max"
  stability = "experimental"
  backends = ["pi"]
  role_exception = "{reason}"
''')
        completed = subprocess.run(
            [
                root / "bin" / "agent-routing",
                "resolve",
                "implement",
                "--backend",
                "pi",
                "--variant",
                "defects",
                "--allow-experimental",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["role_exception"], reason)

    def test_claude_backend_coverage_is_stated(self):
        route = resolve(ROOT, "explore", "claude")
        self.assertEqual(route["profile"], "explore:opus")
        self.assertEqual(route["provider"], "anthropic")
        self.assertEqual(route["model"], "claude-opus-5-5")
        self.assertEqual(route["effort"], "medium")
        self.assertEqual(route["stability"], "stable")

        for profile in ("extract", "plan", "generate", "interactive"):
            with self.subTest(profile=profile):
                with self.assertRaises(RouteRefusal) as caught:
                    resolve(ROOT, profile, "claude")
                self.assertEqual(caught.exception.kind, "unsupported-backend")

    def test_an_unsupported_backend_refusal_names_the_alternatives(self):
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "design", "codex")
        payload = caught.exception.payload()
        self.assertEqual(payload["profile_backends"], ["claude"])
        self.assertIn("implement", payload["backend_routes"])
        self.assertIn("review", payload["backend_routes"])
        self.assertNotIn("design", payload["backend_routes"])

        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "explore", "opencode")
        self.assertEqual(
            caught.exception.payload()["profile_backends"],
            ["claude", "codex", "pi"],
        )



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
