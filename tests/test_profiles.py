import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from routing_profiles import (
    RouteRefusal,
    _review_author,
    assess_review,
    frontier_review,
    model_effort_facts,
    pool_problems,
    route_version,
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
  rank = 1
  floor = 1
  use = "fixture tier"
''')
        self.declare_backend_model_efforts(root, "pi", "fixture-generator", ["max"])
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
                if backend == "pi" and effort == "xhigh":
                    continue
                route = resolve(ROOT, "computer-use", backend, variant_id=variant,
                                allow_experimental=True)
                self.assertEqual((route["model"], route["effort"]), ("gpt-6.1-sol", effort))

    def test_pi_refuses_unmapped_sol_efforts(self):
        for effort in ("xhigh", "max"):
            with self.subTest(effort=effort):
                with self.assertRaises(RouteRefusal) as caught:
                    self.direct_selection(profile_id="computer-use", backend="pi",
                                          model="gpt-6.1-sol", effort=effort,
                                          allow_cross_pool=True)
                self.assertEqual(caught.exception.kind, "unsupported-effort")
                completed = subprocess.run(
                    [ROOT / "bin" / "agent-routing", "validate", "--profile", "computer-use",
                     "--backend", "pi", "--model", "gpt-6.1-sol", "--effort", effort,
                     "--provider", "openai-codex", "--reason", "trial", "--allow-experimental", "--json"],
                    capture_output=True, text=True)
                self.assertEqual(completed.returncode, 1, completed.stdout)
                self.assertEqual(completed.stdout, "")
                self.assertEqual(json.loads(completed.stderr.splitlines()[-1])["kind"], "unsupported-effort")

    def test_pi_cannot_resolve_sol_xhigh_even_with_opt_in(self):
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "computer-use", "pi", variant_id="xhigh", allow_experimental=True)
        self.assertEqual(caught.exception.kind, "unsupported-backend")

    def declare_backend_model_efforts(self, root, backend, model, efforts):
        path = root / "routing" / "delegation.toml"
        text = path.read_text()
        facts = next(row for row in tomllib.loads(text)["backend"] if row["id"] == backend)
        overrides = facts.get("model_efforts", {})
        overrides[model] = efforts
        declaration = 'model_efforts = { ' + ', '.join(
            f'{json.dumps(key)} = {json.dumps(value)}' for key, value in overrides.items()) + ' }'
        start = text.index(f'id = "{backend}"\n', text.index('[[backend]]'))
        end = text.find('\n[[', start)
        end = len(text) if end < 0 else end
        section = '\n'.join(line for line in text[start:end].split('\n')
                            if not line.startswith('model_efforts ='))
        section = section.replace(f'id = "{backend}"\n', f'id = "{backend}"\n{declaration}\n', 1)
        path.write_text(text[:start] + section + text[end:])

    def restrict_backend_efforts(self, root, backend, efforts):
        path = root / "routing" / "delegation.toml"
        text = path.read_text()
        start = text.index(f'id = "{backend}"\n', text.index('[[backend]]'))
        end = text.find('\n[[', start)
        end = len(text) if end < 0 else end
        section = text[start:end]
        section = '\n'.join(line for line in section.split('\n')
                            if not line.startswith(('supported_efforts =', 'model_efforts =')))
        section = section.replace(f'id = "{backend}"\n',
                                  f'id = "{backend}"\nsupported_efforts = {json.dumps(efforts)}\nmodel_efforts = {{}}\n', 1)
        path.write_text(text[:start] + section + text[end:])

    def test_every_backend_enforces_effort_support_in_lint_and_resolution(self):
        for backend, profile in (("codex", "execute"), ("claude", "design"),
                                 ("pi", "generate"), ("opencode", "generate")):
            with self.subTest(backend=backend):
                root = self.fixture_root()
                self.restrict_backend_efforts(root, backend, [])
                if backend == "opencode":
                    path = root / "routing" / "profiles.toml"
                    path.write_text(path.read_text().replace('backends = ["pi"]', 'backends = ["pi", "opencode"]', 1))
                self.assertTrue(any("unsupported effort" in p and backend in p
                                    for p in validation_problems(root)))
                with self.assertRaises(RouteRefusal) as caught:
                    resolve(root, profile, backend)
                self.assertEqual(caught.exception.kind, "manifest-invalid")
                self.assertIn("unsupported effort", caught.exception.message)

    def test_backend_effort_declarations_fail_closed_when_malformed(self):
        for declaration in ('', 'supported_efforts = "high"', 'supported_efforts = ["typo"]',
                            'supported_efforts = ["high", "high"]',
                            'supported_efforts = ["high"]\nmodel_efforts = []',
                            'supported_efforts = ["high"]\nmodel_efforts = { missing = ["max"] }',
                            'supported_efforts = ["high"]\nmodel_efforts = { "gpt-6.1-sol" = "max" }'):
            with self.subTest(declaration=declaration):
                root = self.fixture_root()
                self.restrict_backend_efforts(root, "opencode", [])
                path = root / "routing" / "delegation.toml"
                path.write_text(path.read_text().replace(
                    'supported_efforts = []\nmodel_efforts = {}', declaration, 1))
                self.assertTrue(any("backend 'opencode'" in p and "effort" in p
                                    for p in validation_problems(root)))

    def test_direct_selection_checks_non_pi_backend_efforts(self):
        for backend, model, provider in (("codex", "gpt-6.1-sol", "openai-codex"),
                                         ("claude", "haiku-5.5", "anthropic")):
            with self.subTest(backend=backend):
                root = self.fixture_root()
                self.declare_backend_model_efforts(root, backend, model, ["low", "medium", "high", "xhigh"])
                with self.assertRaises(RouteRefusal) as caught:
                    self.direct_selection(root, backend=backend, model=model, effort="max", provider=provider)
                self.assertEqual(caught.exception.kind, "unsupported-effort")

    def test_sol_max_is_explicit_only_beside_the_computer_use_tiers(self):
        for effort in ("low", "medium", "high", "xhigh", "max"):
            self.direct_selection(profile_id="computer-use", model="gpt-6.1-sol",
                                  effort=effort)
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(profile_id="execute", model="gpt-6.1-sol",
                                  effort="max", allow_experimental=False)
        self.assertEqual(caught.exception.kind, "stability")

    def test_superseded_sol_is_refused_at_every_tier(self):
        for effort in ("low", "medium", "high", "xhigh"):
            with self.assertRaises(RouteRefusal) as caught:
                self.direct_selection(profile_id="computer-use", model="gpt-6-sol",
                                      effort=effort)
            self.assertEqual(caught.exception.kind, "model-role")

    def test_opus_computer_use_requires_explicit_claude_selection(self):
        with self.assertRaises(RouteRefusal):
            resolve(ROOT, "computer-use", "claude", allow_experimental=True)
        with self.assertRaises(RouteRefusal):
            resolve(ROOT, "computer-use", "claude", variant_id="opus")
        route = resolve(ROOT, "computer-use", "claude", variant_id="opus",
                        allow_experimental=True)
        self.assertEqual((route["model"], route["effort"]),
                         ("claude-opus-5-5", "medium"))
        for effort in ("low", "medium", "high", "xhigh"):
            selection = self.direct_selection(
                profile_id="computer-use", backend="claude", model="opus-5.5",
                effort=effort, provider="anthropic",
            )
            self.assertEqual(selection["backend_model"], "claude-opus-5-5")
            self.assertEqual(selection["effort"], effort)
            self.assertEqual(selection["selection_kind"], "operator-directed")
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(profile_id="computer-use", backend="claude", model="opus-5.5",
                                  effort="max", provider="anthropic")
        self.assertEqual(caught.exception.kind, "prohibited")

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
        self.assertEqual(route["effort"], "xhigh")
        self.assertEqual(route["stability"], "stable")

    def test_execute_offers_high_on_claude_by_choice(self):
        route = resolve(ROOT, "execute", "claude", variant_id="opus-high")
        self.assertEqual((route["profile"], route["effort"]), ("execute:opus-high", "high"))

    def test_claude_backend_defaults_follow_the_opus_tiers(self):
        for profile, variant, effort in (("implement", "opus-low", "low"), ("execute", "opus", "low"),
                                         ("plan", "opus", "high"), ("review", "opus", "xhigh")):
            route = resolve(ROOT, profile, "claude")
            self.assertEqual(route["profile"], f"{profile}:{variant}")
            self.assertEqual(route["backend"], "claude")
            self.assertEqual(route["provider"], "anthropic")
            self.assertEqual(route["model"], "claude-opus-5-5")
            self.assertEqual(route["effort"], effort)
            self.assertEqual(route["stability"], "stable")
        design = resolve(ROOT, "design", "claude")
        self.assertEqual((design["model"], design["effort"]), ("claude-opus-5-5", "high"))

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
        self.assertEqual(route["effort"], "xhigh")
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
            "model": "gpt-6.1-sol",
            "effort": "high",
            "provider": "opencode-go",
        }
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(**values)
        self.assertEqual(caught.exception.kind, "pool")
        self.assertEqual(caught.exception.payload()["override"], "--allow-cross-pool")
        route = self.direct_selection(allow_cross_pool=True, **values)
        self.assertEqual(route["cross_pool"], "OpenCode Go, an optional flat subscription")

    def test_direct_selection_of_an_unseated_tier_requires_experimental_opt_in(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(model="gpt-6-astra", effort="xhigh", allow_experimental=False)
        self.assertEqual(caught.exception.kind, "stability")
        payload = caught.exception.payload()
        self.assertEqual(payload["stability"], "experimental")
        self.assertEqual(payload["direction"], "upgrade")
        route = self.direct_selection(model="gpt-6-astra", effort="xhigh")
        self.assertEqual(route["stability"], "experimental")
        self.assertEqual(route["selection_kind"], "operator-directed")

    def test_a_seated_upgrade_is_a_stable_operator_escalation(self):
        route = self.direct_selection(
            profile_id="explore", model="gpt-6-astra", effort="xhigh", allow_experimental=False
        )
        self.assertEqual(route["selection_kind"], "operator-escalation")
        self.assertEqual(route["stability"], "stable")
        self.assertEqual(route["direction"], "upgrade")
        self.assertEqual(route["baseline"], "gpt-6-luna#max")
        self.assertFalse(route["rostered"])

    def test_naming_the_baseline_is_stable_and_directed(self):
        route = self.direct_selection(profile_id="explore", allow_experimental=False)
        self.assertEqual(route["direction"], "same")
        self.assertEqual(route["stability"], "stable")
        self.assertEqual(route["selection_kind"], "operator-directed")

    def test_a_stable_variant_is_stable_only_on_its_own_backend(self):
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        anchor = '  [[profile.variant]]\n  id = "high-stakes"'
        text = profiles.read_text()
        self.assertIn(anchor, text)
        variant = '''  [[profile.variant]]
  id = "luna"
  provider = "openai-codex"
  model = "gpt-6-luna"
  effort = "max"
  stability = "stable"
  backends = ["codex"]

'''
        profiles.write_text(text.replace(anchor, variant + anchor, 1))
        self.declare_backend_model_efforts(root, "pi", "gpt-6-luna", ["max"])
        values = {"root": root, "profile_id": "review", "model": "gpt-6-luna", "effort": "max"}
        route = self.direct_selection(allow_experimental=False, **values)
        self.assertEqual(route["direction"], "downgrade")
        self.assertEqual(route["stability"], "stable")
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(backend="pi", allow_experimental=False, **values)
        self.assertEqual(caught.exception.kind, "stability")

    def test_an_experimental_baseline_keeps_a_direct_selection_experimental(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(profile_id="computer-use", effort="low", allow_experimental=False)
        self.assertEqual(caught.exception.kind, "stability")
        route = self.direct_selection(profile_id="computer-use", effort="low")
        self.assertEqual(route["stability"], "experimental")

    def test_direction_reports_downgrade_and_unranked(self):
        low = self.direct_selection(profile_id="explore", effort="low")
        self.assertEqual(low["direction"], "downgrade")
        self.assertEqual(low["stability"], "experimental")
        unranked = self.direct_selection(profile_id="explore", model="gpt-6-astra", effort="low")
        self.assertEqual(unranked["direction"], "unranked")

    def test_baseline_is_the_canonical_backend_default(self):
        pi = self.direct_selection(
            profile_id="explore", backend="pi", model="deepseek-v4.1-flash", effort="low", provider="opencode-go"
        )
        self.assertEqual(pi["baseline"], "deepseek-flash#low")
        claude = self.direct_selection(
            profile_id="explore", backend="claude", model="opus-5.5", effort="xhigh",
            provider="anthropic", allow_experimental=False,
        )
        self.assertEqual(claude["baseline"], "haiku-5.5#high")
        self.assertEqual(claude["direction"], "upgrade")
        self.assertEqual(claude["stability"], "stable")
        sol = self.direct_selection(
            profile_id="execute", model="gpt-6.1-sol", effort="xhigh",
            allow_experimental=False,
        )
        self.assertEqual(sol["baseline"], "gpt-6.1-sol#xhigh")
        self.assertEqual(sol["stability"], "stable")

    def test_a_profile_without_a_baseline_on_the_backend_stays_experimental(self):
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        old = 'default_for_backend = true'
        # Drop explore's pi default so nothing answers explore on pi without a variant.
        start = text.index('[[profile]]\nid = "explore"')
        end = text.index('[[profile]]', start + 1)
        block = text[start:end]
        self.assertIn(old, block)
        profiles.write_text(text[:start] + block.replace(old, 'default_for_backend = false', 1) + text[end:])
        route = self.direct_selection(
            root, profile_id="explore", backend="pi", model="deepseek-flash", effort="low", provider="opencode-go"
        )
        self.assertIsNone(route["baseline"])
        self.assertEqual(route["direction"], "unranked")
        self.assertEqual(route["stability"], "experimental")

    def test_a_probationary_baseline_caps_a_seated_upgrade(self):
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        text = profiles.read_text()
        start = text.index('[[profile]]\nid = "explore"')
        stability = text.index('stability = "stable"', start)
        profiles.write_text(text[:stability] + 'stability = "probationary"' + text[stability + len('stability = "stable"'):])
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                root, profile_id="explore", model="gpt-6-astra", effort="xhigh", allow_experimental=False
            )
        self.assertEqual(caught.exception.kind, "stability")

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

    def test_haiku_5_5_is_an_explicit_claude_trial_without_reseating_defaults(self):
        for model in ("haiku-5.5", "haiku-5-5", "claude-haiku-5-5"):
            for effort in ("low", "medium", "high", "xhigh", "max"):
                with self.subTest(model=model, effort=effort):
                    selection = self.direct_selection(
                        profile_id="implement",
                        backend="claude",
                        model=model,
                        effort=effort,
                        provider="anthropic",
                    )
                    self.assertEqual(selection["canonical_model"], "haiku-5.5")
                    self.assertEqual(selection["backend_model"], "claude-haiku-5-5")
                    self.assertEqual(selection["stability"], "experimental")
                    self.assertEqual(selection["selection_kind"], "operator-directed")
                    self.assertFalse(selection["rostered"])
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                profile_id="implement",
                backend="claude",
                model="haiku-5.5",
                effort="medium",
                provider="anthropic",
                allow_experimental=False,
            )
        self.assertEqual(caught.exception.kind, "stability")
        self.assertEqual(resolve(ROOT, "implement", "codex")["model"], "gpt-6-luna")
        self.assertEqual(resolve(ROOT, "implement", "pi")["model"], "deepseek-v4.1-flash")
        self.assertEqual(resolve(ROOT, "implement", "claude")["model"], "claude-opus-5-5")

    def test_deprecated_claude_models_are_outside_the_served_pool(self):
        pools = tomllib.loads((ROOT / "routing" / "delegation.toml").read_text())["pool"]
        served = set(next(pool for pool in pools if pool["provider"] == "anthropic")["serves"])
        self.assertIn("haiku-5.5", served)
        self.assertTrue({"opus-5", "fable-5", "sonnet-5", "haiku-4.5"}.isdisjoint(served))
        for model in ("opus-5", "fable-5", "sonnet-5", "haiku-4.5"):
            with self.subTest(model=model), self.assertRaises(RouteRefusal):
                self.direct_selection(
                    profile_id="implement",
                    backend="claude",
                    model=model,
                    effort="medium",
                    provider="anthropic",
                )

    def test_haiku_trial_tiers_are_named_under_every_model_id(self):
        command = ROOT / "bin" / "routing-check"
        for model in ("haiku-5.5", "haiku-5-5", "claude-haiku-5-5"):
            for effort in ("low", "xhigh", "max"):
                with self.subTest(model=model, effort=effort):
                    completed = subprocess.run([command, model, effort], capture_output=True, text=True)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertIn(f"explicit-only: haiku-5.5 at {effort}", completed.stdout)
        for effort in ("medium", "high"):
            with self.subTest(effort=effort):
                completed = subprocess.run([command, "haiku-5.5", effort], capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn(f"not prohibited: haiku-5.5 at {effort}", completed.stdout)

    def test_sonnet_5_5_is_an_experimental_selection_at_every_tier(self):
        for model in ("sonnet-5.5", "sonnet-5-5", "claude-sonnet-5-5"):
            for effort in ("low", "medium", "high", "xhigh", "max"):
                with self.subTest(model=model, effort=effort):
                    selection = self.direct_selection(
                        profile_id="implement",
                        backend="claude",
                        model=model,
                        effort=effort,
                        provider="anthropic",
                    )
                    self.assertEqual(selection["canonical_model"], "sonnet-5.5")
                    self.assertEqual(selection["backend_model"], "claude-sonnet-5-5")
                    self.assertEqual(selection["effort"], effort)
                    self.assertEqual(selection["stability"], "experimental")
                    self.assertEqual(selection["selection_kind"], "operator-directed")
                    self.assertFalse(selection["rostered"])

    def test_sonnet_5_5_max_still_requires_the_experimental_opt_in(self):
        with self.assertRaises(RouteRefusal) as caught:
            self.direct_selection(
                profile_id="implement",
                backend="claude",
                model="sonnet-5.5",
                effort="max",
                provider="anthropic",
                allow_experimental=False,
            )
        self.assertEqual(caught.exception.kind, "stability")

    def test_check_names_sonnet_5_5_max_explicit_only_under_every_name(self):
        command = ROOT / "bin" / "routing-check"
        for argument in ("sonnet-5.5", "sonnet-5-5", "claude-sonnet-5-5"):
            for effort in ("low", "xhigh", "max"):
                with self.subTest(argument=argument, effort=effort):
                    completed = subprocess.run([command, argument, effort], capture_output=True, text=True)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertIn(f"explicit-only: sonnet-5.5 at {effort}", completed.stdout)
        for effort in ("medium", "high"):
            with self.subTest(effort=effort):
                completed = subprocess.run([command, "sonnet-5.5", effort], capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn(f"not prohibited: sonnet-5.5 at {effort}", completed.stdout)

    def test_sonnet_5_5_max_cannot_back_a_profile(self):
        root = self.fixture_root()
        self.add_implement_variant(
            root,
            '''  [[profile.variant]]
  id = "sonnet-max"
  provider = "anthropic"
  model = "sonnet-5.5"
  backend_model = "claude-sonnet-5-5"
  effort = "max"
  stability = "experimental"
  backends = ["claude"]
''',
        )
        self.assertTrue(
            any(
                "sonnet-5.5 max requires an explicit model request and cannot back a profile" in problem
                for problem in validation_problems(root)
            )
        )

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
        self.assertEqual((route["model"], route["effort"]), ("gpt-6.1-sol", "xhigh"))
        self.assertEqual(route["stability"], "stable")

        astra = resolve(ROOT, "review", "codex", variant_id="astra")
        self.assertEqual((astra["model"], astra["effort"]), ("gpt-6-astra", "medium"))
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
model = "haiku-5.5"
effort = "low"
stability = "stable"
backends = ["claude"]
''')
        self.assertTrue(any("requires an explicit model request" in problem for problem in validation_problems(root)))

    def test_unknown_model_and_unverified_backend_are_rejected(self):
        root = self.fixture_root()
        profiles = root / "routing" / "profiles.toml"
        profiles.write_text(profiles.read_text().replace('model = "gpt-6-luna"', 'model = "missing-model"', 1))
        delegation = root / "routing" / "delegation.toml"
        text = delegation.read_text()
        prefix, backend_tables = text.split('[[backend]]', 1)
        delegation.write_text(prefix + '[[backend]]' + backend_tables.replace(
            'status = "verified"', 'status = "unprobed"', 1))
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
        explicit = subprocess.run([command, "haiku-5.5", "low"], capture_output=True, text=True)
        self.assertEqual(explicit.returncode, 0)
        self.assertIn("explicit-only", explicit.stdout)
        restricted = subprocess.run([command, "sonnet-5", "low"], capture_output=True, text=True)
        self.assertEqual(restricted.returncode, 0)
        self.assertIn("restricted", restricted.stdout)
        for model in ("opus-5", "opus-4.8"):
            with self.subTest(model=model):
                superseded = subprocess.run([command, model, "high" if model == "opus-4.8" else "medium"], capture_output=True, text=True)
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
  model = "gpt-6.1-sol"
  effort = "xhigh"
  stability = "stable"
  backends = ["pi"]

'''
        profiles.write_text(text.replace(anchor, variant + anchor, 1))
        self.declare_backend_model_efforts(root, "pi", "gpt-6.1-sol", ["low", "medium", "high", "xhigh"])
        return root

    def test_a_pool_refusal_names_the_subscription_that_pays(self):
        root = self.cross_pool_root()
        with self.assertRaises(RouteRefusal) as caught:
            resolve(root, "review", "pi", variant_id="go-sol")
        refusal = caught.exception
        self.assertEqual(refusal.kind, "pool")
        payload = refusal.payload()
        self.assertEqual(payload["model"], "gpt-6.1-sol")
        self.assertEqual(payload["override"], "--allow-cross-pool")
        self.assertIn("openai-codex", payload["alternative"])

    def test_crossing_a_pool_is_opt_in_and_recorded(self):
        root = self.cross_pool_root()
        route = resolve(root, "review", "pi", variant_id="go-sol", allow_cross_pool=True)
        self.assertEqual(route["model"], "gpt-6.1-sol")
        self.assertIn("cross_pool", route)

    def test_one_pool_violation_does_not_block_an_unrelated_route(self):
        """A pool pairing is a property of one route. Blocking every other
        resolution would make a single bad variant an outage."""
        root = self.cross_pool_root()
        self.assertEqual(resolve(root, "review", "codex")["model"], "gpt-6.1-sol")
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
            self.assertEqual(route["effort"], "low" if profile == "explore" else "max")
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
        for profile in ("explore", "extract"):
            with self.subTest(profile=profile):
                route = resolve(ROOT, profile, "claude")
                self.assertEqual(route["profile"], f"{profile}:haiku")
                self.assertEqual(route["provider"], "anthropic")
                self.assertEqual(route["model"], "claude-haiku-5-5")
                self.assertEqual(route["effort"], "high")
                self.assertEqual(route["stability"], "stable")

        route = resolve(ROOT, "plan", "claude")
        self.assertEqual((route["profile"], route["model"], route["effort"]),
                         ("plan:opus", "claude-opus-5-5", "high"))

        for profile in ("generate", "interactive"):
            with self.subTest(profile=profile):
                with self.assertRaises(RouteRefusal) as caught:
                    resolve(ROOT, profile, "claude")
                self.assertEqual(caught.exception.kind, "unsupported-backend")

    def test_explore_keeps_opus_selectable_on_claude(self):
        route = resolve(ROOT, "explore", "claude", variant_id="opus")
        self.assertEqual(route["profile"], "explore:opus")
        self.assertEqual(route["model"], "claude-opus-5-5")
        self.assertEqual(route["effort"], "high")
        self.assertEqual(route["stability"], "stable")

    def test_haiku_is_served_by_the_claude_backend_alone(self):
        for profile in ("extract", "explore"):
            for backend in ("codex", "pi", "opencode"):
                with self.subTest(profile=profile, backend=backend):
                    try:
                        route = resolve(ROOT, profile, backend)
                    except RouteRefusal:
                        continue
                    self.assertNotEqual(route["model"], "claude-haiku-5-5")
                    self.assertNotEqual(route["provider"], "anthropic")
        pools = tomllib.loads((ROOT / "routing" / "delegation.toml").read_text())["pool"]
        for pool in pools:
            if pool["provider"] != "anthropic":
                self.assertNotIn("haiku-5.5", pool["serves"])
        profiles = tomllib.loads((ROOT / "routing" / "profiles.toml").read_text())["profile"]
        for profile in profiles:
            for route in [profile, *profile.get("variant", [])]:
                if route.get("model") == "haiku-5.5":
                    self.assertEqual(route["backends"], ["claude"])
                    self.assertEqual(route["provider"], "anthropic")

    def test_haiku_high_alone_is_the_stable_tier(self):
        models = tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]
        haiku = next(model for model in models if model["id"] == "haiku-5.5")
        self.assertNotIn("status", haiku)
        tiers = {tier["effort"]: tier.get("status") for tier in haiku["effort"]}
        self.assertEqual(
            tiers,
            {
                "low": "explicit-only",
                "medium": "probationary",
                "high": None,
                "xhigh": "explicit-only",
                "max": "explicit-only",
            },
        )

    def test_cache_hit_prices_follow_the_published_multipliers(self):
        models = tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]
        prices = {
            model["id"]: model["api_price_per_million"] for model in models if "api_price_per_million" in model
        }
        self.assertEqual(prices["sonnet-5.5"]["cached_input"], 0.10)
        self.assertEqual(prices["opus-5.5"]["cached_input"], 0.20)
        self.assertEqual(prices["fable-5.1"]["cached_input"], 0.25)
        self.assertEqual(prices["haiku-5.5"]["cached_input"], 0.01)

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


class ReviewAuthorTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        shutil.copytree(ROOT / "routing", root / "routing")
        return root

    def malformed_family_root(self, value):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        replacement = '' if value is None else f'family = {value}\n'
        path.write_text(path.read_text().replace(
            'id = "gpt-6-luna"\nfamily = "openai"\n',
            'id = "gpt-6-luna"\n' + replacement, 1))
        return root

    def test_malformed_author_families_fail_closed(self):
        for value in (None, '""', '"  "', '17', '[]', '{}'):
            with self.subTest(value=value):
                root = self.malformed_family_root(value)
                problems = validation_problems(root)
                self.assertTrue(any("family must be a nonblank string" in p for p in problems), problems)
                with self.assertRaises(RouteRefusal) as caught:
                    resolve(root, "review", "codex", author="gpt-6-luna#max")
                self.assertEqual(caught.exception.kind, "manifest-invalid")

    def test_author_reader_refuses_malformed_families_before_lineage_comparison(self):
        for value in (None, '""', '"  "', '17', '[]', '{}'):
            with self.subTest(value=value):
                with self.assertRaises(RouteRefusal) as caught:
                    _review_author(self.malformed_family_root(value), "gpt-6-luna#max", "review", "codex")
                self.assertEqual(caught.exception.payload()["reason"], "unknown-author-family")
                self.assertEqual(caught.exception.payload()["recommendation"], "record-debt")

    def test_superseded_sol_author_resolves_an_independent_claude_peer(self):
        result = subprocess.run(
            [ROOT / "bin" / "agent-routing", "resolve", "review", "--backend", "claude",
             "--author", "gpt-6-sol#xhigh", "--json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        route = json.loads(result.stdout)
        self.assertEqual((route["model"], route["effort"]), ("claude-opus-5-5", "xhigh"))
        self.assertEqual(route["review"]["independence"], "eligible")
        self.assertEqual(route["review"]["author_tier"], 2)

    def assess(self, reviewer, *authors, root=ROOT):
        return assess_review(root, reviewer, list(authors))

    def test_assessment_of_a_same_family_read_at_the_floor_is_ineligible(self):
        result = self.assess("opus-5.5#xhigh", "sonnet-5.5#high")
        self.assertEqual(result["schema"], "agent-routing-assessment/2")
        self.assertEqual(result["route_version"], route_version(ROOT))
        self.assertEqual(result["reviewer"]["review_tier"], 2)
        self.assertEqual(result["authors"], [
            {"model": "sonnet-5.5", "effort": "high", "family": "claude", "floor": 2,
             "identities": ["claude-sonnet-5-5", "sonnet-5-5", "sonnet-5.5"]}])
        self.assertEqual(result["floor"], 2)
        self.assertEqual(result["qualifiers"], ["same-family"])
        self.assertEqual((result["independence"], result["debt_kind"]), ("ineligible", "ineligible-review"))

    def test_assessment_of_a_cross_family_read_at_the_floor_is_eligible(self):
        result = self.assess("gpt-6.1-sol#xhigh", "opus-5.5#xhigh")
        self.assertEqual((result["independence"], result["qualifiers"], result["debt_kind"]),
                         ("eligible", [], None))

    def test_assessment_names_a_same_family_read_below_the_floor(self):
        result = self.assess("haiku-5.5#high", "opus-5.5#xhigh")
        self.assertEqual(result["qualifiers"], ["same-family", "below-floor", "below-clearance"])

    def test_assessment_names_a_cross_family_read_below_the_floor_alone(self):
        result = self.assess("gpt-6.1-sol#xhigh", "opus-5.5#max")
        self.assertEqual(result["qualifiers"], ["below-floor"])

    def test_assessment_of_an_unseated_reviewer_is_not_below_floor(self):
        result = self.assess("sonnet-5.5#high", "gpt-6.1-sol#xhigh")
        self.assertEqual(result["reviewer"]["review_tier"], 2)
        self.assertEqual(result["qualifiers"], ["reviewer-unseated"])

    def test_assessment_unions_qualifiers_across_authors(self):
        result = self.assess("opus-5.5#xhigh", "opus-5.5#xhigh", "sonnet-5.5#high")
        self.assertEqual(result["qualifiers"], ["same-model", "same-family"])
        result = self.assess("gpt-6.1-sol#xhigh", "opus-5.5#xhigh", "opus-5.5#max")
        self.assertEqual((result["floor"], result["qualifiers"]), (3, ["below-floor"]))

    def test_assessment_names_every_identity_routing_accepts_for_each_model(self):
        result = self.assess("opus-5.5#xhigh", "sonnet-5.5#high", "gpt-6.1-sol#xhigh")
        self.assertLessEqual({"opus-5.5", "opus-5-5", "claude-opus-5-5"}, set(result["reviewer"]["identities"]))
        for row in (result["reviewer"], *result["authors"]):
            with self.subTest(model=row["model"]):
                self.assertEqual(row["identities"], sorted(set(row["identities"])))
                self.assertIn(row["model"], row["identities"])
                for identity in row["identities"]:
                    self.assertEqual(model_effort_facts(ROOT, identity)["model_id"], row["model"], identity)

    def test_assessment_never_infers_a_missing_floor(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        path.write_text(path.read_text().replace('  floor = 3\n', '', 1))
        result = self.assess("gpt-6.1-sol#xhigh", "opus-5.5", root=root)
        self.assertEqual((result["floor"], result["authors"][0]["floor"]), (None, None))
        self.assertEqual(result["qualifiers"], ["floor-unknown"])

    def test_assessment_resolves_aliases_and_refuses_unknown_coordinates(self):
        self.assertEqual(self.assess("claude-opus-5-5#xhigh", "opus-5.5#xhigh")["reviewer"]["model"], "opus-5.5")
        for reviewer, authors in (("nonesuch#high", ["opus-5.5#xhigh"]),
                                  ("opus-5.5#xhigh", ["nonesuch#high"]),
                                  ("opus-5.5#nonesuch", ["opus-5.5#xhigh"]),
                                  ("opus-5.5#xhigh", [])):
            with self.subTest(reviewer=reviewer, authors=authors), self.assertRaises(RouteRefusal) as caught:
                assess_review(ROOT, reviewer, authors)
            self.assertEqual(caught.exception.kind, "unknown-coordinate")

    def test_assess_cli_emits_json_and_a_text_line_and_refuses_an_unknown_model(self):
        run = lambda *args: subprocess.run([ROOT / "bin" / "agent-routing", "assess", *args],
                                           capture_output=True, text=True)
        result = run("--reviewer", "opus-5.5#xhigh", "--author", "opus-5.5#xhigh",
                     "--author", "sonnet-5.5#high", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["qualifiers"], ["same-model", "same-family"])
        result = run("--reviewer", "haiku-5.5#high", "--author", "opus-5.5#xhigh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertIn("same-family,below-floor", result.stdout)
        result = run("--reviewer", "nonesuch#high", "--author", "opus-5.5#xhigh", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr.splitlines()[-1])["kind"], "unknown-coordinate")
        self.assertEqual(result.stdout, "")

    def test_accept_ineligible_returns_the_strongest_seat_with_a_prefilled_debt_kind(self):
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "review", "claude", author="sonnet-5.5#high")
        self.assertEqual(caught.exception.payload()["recommendation"], "record-debt")
        route = resolve(ROOT, "review", "claude", author="sonnet-5.5#high", accept_ineligible=True)
        self.assertEqual((route["model"], route["effort"]), ("claude-opus-5-5", "xhigh"))
        review = route["review"]
        self.assertEqual(review["independence"], "ineligible")
        self.assertEqual(review["qualifiers"], ["same-family"])
        self.assertEqual((review["recommendation"], review["debt_kind"]), ("record-debt", "ineligible-review"))

    def test_accept_ineligible_leaves_an_eligible_route_unchanged(self):
        plain = resolve(ROOT, "review", "codex", author="opus-5.5#xhigh")
        self.assertEqual(resolve(ROOT, "review", "codex", author="opus-5.5#xhigh", accept_ineligible=True), plain)
        self.assertEqual(plain["review"]["independence"], "eligible")

    def test_accept_ineligible_ranks_seats_by_review_tier(self):
        route = resolve(ROOT, "review", "codex", author="opus-5.5#max", accept_ineligible=True)
        self.assertEqual(route["review"]["reviewer_tier"], 3)
        self.assertEqual(route["review"]["qualifiers"], [])
        self.assertTrue(route["review"]["clears"])

    def test_accept_ineligible_covers_an_unknown_floor_and_needs_an_author(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        path.write_text(path.read_text().replace('  floor = 3\n', '', 1))
        with self.assertRaises(RouteRefusal) as caught:
            resolve(root, "review", "codex", author="opus-5.5", accept_ineligible=True)
        self.assertEqual(caught.exception.kind, "manifest-invalid")
        for kwargs in ({"author": None}, {"author": "nonesuch#high"}):
            with self.subTest(**kwargs), self.assertRaises(RouteRefusal):
                resolve(ROOT, "review", "codex", accept_ineligible=True, **kwargs)

    def test_shipped_superseded_authors_have_conservative_floors_at_every_effort(self):
        models = {model["id"]: model for model in
                  tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]}
        for author, successor in (("gpt-6-sol", "gpt-6.1-sol"),
                                  ("gpt-5.6-luna", "gpt-6-luna")):
            successor_tiers = {tier["effort"]: tier.get("floor")
                               for tier in models[successor]["effort"]}
            for tier in models[author]["effort"]:
                with self.subTest(author=author, effort=tier["effort"]):
                    self.assertIn("floor", tier)
                    self.assertGreaterEqual(tier["floor"], successor_tiers[tier["effort"]])
                    self.assertNotIn("review_tier", tier)
                    self.assertTrue(models[author]["effort"])
                    if tier["floor"] > 2:
                        with self.assertRaises(RouteRefusal) as caught:
                            resolve(ROOT, "review", "claude", author=f"{author}#{tier['effort']}")
                        self.assertEqual(caught.exception.payload()["reason"], "no-eligible-route")
                        self.assertEqual(caught.exception.payload()["author_tier"], tier["floor"])
                    else:
                        route = resolve(ROOT, "review", "claude", author=f"{author}#{tier['effort']}")
                        self.assertEqual(route["review"]["author_tier"], tier["floor"])

    def test_lint_requires_floors_on_superseded_tiers(self):
        root = self.fixture_root()
        path = root / "routing/models.toml"
        path.write_text(path.read_text() + '\n[[model]]\nid = "fixture-retired"\nfamily = "fixture"\nstatus = "superseded"\n[[model.effort]]\neffort = "high"\nrank = 1\n')
        self.assertTrue(any("floor must be a positive integer" in p for p in validation_problems(root)))
        with self.assertRaises(RouteRefusal) as caught:
            resolve(root, "review", "claude", author="fixture-retired#high")
        self.assertEqual(caught.exception.kind, "manifest-invalid")

    def test_trial_floor_resolves_a_stable_codex_peer(self):
        result = subprocess.run(
            [ROOT / "bin" / "agent-routing", "resolve", "review", "--backend", "codex",
             "--author", "claude-sonnet-5-5#xhigh", "--json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        route = json.loads(result.stdout)
        self.assertEqual((route["model"], route["effort"]), ("gpt-6.1-sol", "xhigh"))
        self.assertEqual(route["stability"], "stable")
        self.assertEqual(route["review"]["independence"], "eligible")
        self.assertEqual(route["review"]["author_tier"], 2)

    def test_trial_max_and_omitted_effort_reach_the_deep_independent_tier(self):
        for author in ("claude-sonnet-5-5#max", "sonnet-5.5"):
            with self.subTest(author=author):
                review = resolve(ROOT, "review", "codex", author=author)["review"]
                self.assertEqual(review["author_tier"], 3)
                self.assertTrue(review["clears"])

    def test_trial_floors_cover_each_effort_without_waiving_family_exclusions(self):
        for effort, floor in (("low", 1), ("medium", 1), ("high", 2), ("xhigh", 2)):
            with self.subTest(effort=effort):
                route = resolve(ROOT, "review", "codex", author=f"sonnet-5.5#{effort}")
                self.assertEqual(route["review"]["author_tier"], floor)
                with self.assertRaises(RouteRefusal) as caught:
                    resolve(ROOT, "review", "claude", author=f"sonnet-5.5#{effort}")
                self.assertEqual(caught.exception.payload()["reason"], "no-eligible-route")

    def test_omitted_effort_refuses_an_incomplete_mix_of_author_fields(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        text = path.read_text()
        path.write_text(text.replace('  floor = 3\n', '', 1))
        with self.assertRaises(RouteRefusal) as caught:
            resolve(root, "review", "codex", author="opus-5.5")
        self.assertEqual(caught.exception.kind, "manifest-invalid")

    def test_trial_capability_does_not_add_a_routing_seat(self):
        models = tomllib.loads((ROOT / "routing/models.toml").read_text())["model"]
        sonnet = next(model for model in models if model["id"] == "sonnet-5.5")
        self.assertEqual({tier["effort"]: tier["floor"] for tier in sonnet["effort"]},
                         {"max": 3, "xhigh": 2, "high": 2, "medium": 1, "low": 1})
        profiles = tomllib.loads((ROOT / "routing/profiles.toml").read_text())["profile"]
        for profile in profiles:
            for route in (profile, *profile.get("variant", [])):
                self.assertNotEqual(route["model"], "sonnet-5.5")
        answer = assess_review(ROOT, "sonnet-5.5#high", ["gpt-6.1-sol#high"])
        self.assertTrue(answer["clears"])
        self.assertEqual(answer["qualifiers"], ["reviewer-unseated"])

    def test_lint_cli_requires_capability_on_an_unseated_tier(self):
        for field in ("rank", "floor"):
            with self.subTest(field=field):
                root = self.fixture_root()
                for directory in ("bin", "lib", "doctrine"):
                    shutil.copytree(ROOT / directory, root / directory)
                path = root / "routing/models.toml"
                text = path.read_text()
                start = text.index('id = "sonnet-5.5"')
                path.write_text(text[:start] + text[start:].replace(f'  {field} = 2\n', '', 1))
                result = subprocess.run([root / "bin/lint-routing"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(f"{field} must be a positive integer", result.stdout)

    def test_floor_lint_rejects_nonpositive_or_noninteger_values(self):
        for value in ("true", "0", "-1", "1.5", '"2"'):
            with self.subTest(value=value):
                root = self.fixture_root()
                path = root / "routing" / "models.toml"
                text = path.read_text()
                start = text.index('id = "sonnet-5.5"')
                path.write_text(text[:start] + text[start:].replace('  floor = 2',
                                                                 f'  floor = {value}', 1))
                self.assertTrue(any("floor must be a positive integer" in problem
                                    for problem in validation_problems(root)))

    def test_gpt_author_keeps_the_opus_route(self):
        for author in ("gpt-6-luna#max", "gpt-6-luna#medium", "gpt-6.1-sol#xhigh",
                       "gpt-6.1-sol#high", "gpt-6-astra#medium"):
            for variant in (None, "opus"):
                with self.subTest(author=author, variant=variant):
                    baseline = resolve(ROOT, "review", "claude", variant_id=variant)
                    route = resolve(ROOT, "review", "claude", variant_id=variant, author=author)
                    self.assertEqual(
                        {key: value for key, value in route.items() if key != "review"},
                        {key: value for key, value in baseline.items() if key != "review"},
                    )
                    self.assertEqual(route["review"]["independence"], "eligible")
                    self.assertGreaterEqual(route["review"]["reviewer_tier"], route["review"]["author_tier"])

    def test_claude_author_cannot_use_claude_for_independent_review(self):
        for author in ("opus-5.5#xhigh", "claude-opus-5-5#xhigh", "opus-5-5#medium"):
            with self.subTest(author=author), self.assertRaises(RouteRefusal) as caught:
                resolve(ROOT, "review", "claude", author=author, allow_experimental=True, allow_cross_pool=True)
            payload = caught.exception.payload()
            self.assertEqual(payload["kind"], "review-independence")
            self.assertEqual(payload["author_family"], "claude")
            self.assertEqual(payload["recommendation"], "record-debt")
            self.assertIn("record Arc review debt", payload["message"])

    def test_author_above_every_offered_review_tier_is_refused(self):
        for backend in ("codex", "claude", "pi"):
            with self.subTest(backend=backend), self.assertRaises(RouteRefusal) as caught:
                resolve(ROOT, "review", backend, author="gpt-6-astra#max")
            self.assertEqual(caught.exception.payload()["author_tier"], 3)
            self.assertEqual(caught.exception.payload()["recommendation"], "record-debt")

    def test_missing_author_exposes_constraints_on_every_review_route(self):
        cases = (("codex", None, "openai"), ("codex", "astra", "openai"),
                 ("codex", "high-stakes", "openai"), ("claude", None, "claude"),
                 ("pi", None, "deepseek"))
        for backend, variant, family in cases:
            with self.subTest(backend=backend, variant=variant):
                review = resolve(ROOT, "review", backend, variant_id=variant)["review"]
                self.assertIsNone(review["author"])
                self.assertEqual(review["independence"], "unverified")
                self.assertIn(family, review["excluded_author_families"])
                self.assertGreater(review["reviewer_tier"], 0)

    def test_opus_author_can_use_the_codex_peer(self):
        route = resolve(ROOT, "review", "codex", author="opus-5.5#xhigh")
        self.assertEqual(route["profile"], "review")
        self.assertEqual(route["review"]["independence"], "eligible")

    def test_unknown_author_facts_recommend_debt(self):
        for author, reason in (("missing#xhigh", "unknown-author"),
                               ("opus-5.5#ultra", "unknown-author-effort"),
                                                              ("", "unknown-author")):
            with self.subTest(author=author), self.assertRaises(RouteRefusal) as caught:
                resolve(ROOT, "review", "codex", author=author)
            self.assertEqual(caught.exception.payload()["reason"], reason)
            self.assertEqual(caught.exception.payload()["recommendation"], "record-debt")

    def test_omitted_effort_uses_the_highest_declared_floor(self):
        self.assertEqual(resolve(ROOT, "review", "claude", author="gpt-6.1-sol")["review"]["author_tier"], 2)
        self.assertEqual(resolve(ROOT, "review", "claude", author="gpt-6-luna")["review"]["author_tier"], 1)

    def test_backend_default_can_escalate_but_an_explicit_variant_cannot(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        text = path.read_text()
        anchor = '  effort = "xhigh"\n  rank = 2\n  floor = 2\n  seat_rank = { "anthropic" = 5 }'
        self.assertIn(anchor, text)
        path.write_text(text.replace(anchor, anchor.replace('floor = 2', 'floor = 3'), 1))
        route = resolve(root, "review", "codex", author="opus-5.5#xhigh")
        self.assertEqual(route["profile"], "review:high-stakes")
        with self.assertRaises(RouteRefusal):
            resolve(root, "review", "codex", variant_id="astra", author="opus-5.5#xhigh")

    def test_experimental_opt_in_does_not_establish_independence(self):
        root = self.fixture_root()
        path = root / "routing" / "profiles.toml"
        text = path.read_text()
        start = text.index('  id = "high-stakes"')
        path.write_text(text[:start] + text[start:].replace('stability = "stable"', 'stability = "experimental"', 1))
        with self.assertRaises(RouteRefusal) as caught:
            resolve(root, "review", "codex", variant_id="high-stakes", author="opus-5.5#xhigh", allow_experimental=True)
        self.assertEqual(caught.exception.kind, "review-independence")

    def test_lint_rejects_a_family_with_surrounding_whitespace(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        self.assertIn('family = "claude"', path.read_text())
        path.write_text(path.read_text().replace('family = "claude"', 'family = " claude "', 1))
        self.assertTrue(any("surrounding whitespace" in problem for problem in validation_problems(root)),
                        validation_problems(root))

    def test_a_padded_family_cannot_mark_a_same_family_reviewer_eligible(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        text = path.read_text()
        start = text.index('id = "sonnet-5.5"')
        path.write_text(text[:start] + text[start:].replace('family = "claude"', 'family = " claude "', 1))
        result = self.assess("opus-5.5#xhigh", "sonnet-5.5#high", root=root)
        self.assertEqual(result["qualifiers"], ["same-family"])
        self.assertEqual(result["authors"][0]["family"], "claude")
        self.assertEqual(_review_author(root, "sonnet-5.5#high", "review", "claude")["family"], "claude")

    def test_review_policy_lint_rejects_invalid_or_missing_tiers(self):
        for replacement in ('rank = true', 'rank = 0', ''):
            root = self.fixture_root()
            path = root / "routing" / "models.toml"
            path.write_text(path.read_text().replace('rank = 2', replacement, 1))
            with self.subTest(replacement=replacement):
                self.assertTrue(any("rank" in problem for problem in validation_problems(root)))

    def test_author_is_only_valid_for_review(self):
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "implement", "codex", author="opus-5.5#xhigh")
        self.assertEqual(caught.exception.kind, "invalid-author")
        self.assertNotIn("review", resolve(ROOT, "implement", "codex"))

    def test_cli_author_contract_and_caller_environment(self):
        command = [ROOT / "bin" / "agent-routing", "resolve", "review", "--backend", "claude", "--json"]
        cases = (([], 0), (["--author", "gpt-6.1-sol#xhigh"], 0),
                 (["--author", "opus-5.5#xhigh"], 1), (["--author", "gpt-6.1-sol#max"], 0))
        for arguments, status in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(command + arguments, capture_output=True, text=True,
                                        env={**os.environ, "ARC_MODEL": "opus-5.5#xhigh"})
                self.assertEqual(result.returncode, status, result.stderr)
                if status:
                    self.assertEqual(result.stdout, "")
                    refusal = json.loads(result.stderr.splitlines()[-1])
                    self.assertEqual(refusal["schema"], "agent-routing-refusal/1")
                    self.assertEqual(refusal["recommendation"], "record-debt")
                else:
                    self.assertEqual(result.stderr, "")
                    review = json.loads(result.stdout)["review"]
                    self.assertEqual(review["independence"], "eligible" if arguments else "unverified")


class ReviewFrontierTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        shutil.copytree(ROOT / "routing", root / "routing")
        return root

    def seats(self, answer):
        return sorted((seat["model"], seat["effort"], seat["backend"], seat["pool"])
                      for seat in answer["frontier"]["seats"])

    def test_a_current_claude_author_has_the_strongest_cross_family_seat_as_its_frontier(self):
        answer = frontier_review(ROOT, "opus-5.5#xhigh")
        self.assertEqual(answer["schema"], "agent-routing-frontier/1")
        self.assertEqual(answer["route_version"], route_version(ROOT))
        self.assertEqual(answer["status"], "frontier")
        self.assertEqual(answer["author"]["model"], "opus-5.5")
        self.assertEqual(answer["author"]["floor"], 2)
        self.assertEqual(answer["frontier"]["review_tier"], 3)
        self.assertEqual(self.seats(answer), [("gpt-6-astra", "xhigh", "codex", "openai-codex")])
        self.assertEqual(answer["reads"], [])

    def test_every_seat_at_the_frontier_tier_is_listed_per_backend_and_pool(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        # Seat a second tier-3 reviewer on the same scale.
        path.write_text(path.read_text().replace('rank = 2\n  floor = 2\n  seat_rank = { "openai-codex" = 3 }',
                                                 'rank = 3\n  floor = 2\n  seat_rank = { "openai-codex" = 3 }', 1))
        answer = frontier_review(root, "opus-5.5#xhigh")
        self.assertEqual(answer["frontier"]["review_tier"], 3)
        self.assertEqual(self.seats(answer), [
            ("gpt-6-astra", "xhigh", "codex", "openai-codex"),
            ("gpt-6.1-sol", "xhigh", "codex", "openai-codex"),
        ])

    def test_a_superseded_author_with_a_recorded_floor_has_a_frontier(self):
        answer = frontier_review(ROOT, "gpt-6-sol#xhigh")
        self.assertEqual((answer["status"], answer["author"]["floor"]), ("frontier", 2))
        self.assertEqual(answer["frontier"]["review_tier"], 2)
        self.assertEqual({seat["model"] for seat in answer["frontier"]["seats"]}, {"opus-5.5"})
        self.assertEqual({seat["pool"] for seat in answer["frontier"]["seats"]}, {"anthropic"})

    def test_an_author_without_a_floor_has_floor_unknown_and_no_frontier(self):
        root = self.fixture_root()
        path = root / "routing/models.toml"
        path.write_text(path.read_text().replace('  floor = 3\n', '', 1))
        answer = frontier_review(root, "opus-5.5#max")
        self.assertEqual((answer["status"], answer["frontier"]), ("floor-unknown", None))
        self.assertIsNone(answer["author"]["floor"])

    def test_an_author_without_effort_and_an_unknown_floor_is_floor_unknown(self):
        root = self.fixture_root()
        path = root / "routing/models.toml"
        path.write_text(path.read_text().replace('  floor = 3\n', '', 1))
        self.assertEqual(frontier_review(root, "opus-5.5")["status"], "floor-unknown")

    def test_a_floor_no_seat_reaches_has_no_eligible_seat(self):
        answer = frontier_review(ROOT, "gpt-6-astra#max")
        self.assertEqual((answer["status"], answer["frontier"]), ("no-eligible-seat", None))
        self.assertEqual(answer["author"]["floor"], 3)

    def test_a_same_family_seat_is_never_on_the_frontier(self):
        answer = frontier_review(ROOT, "gpt-6.1-sol#xhigh")
        self.assertEqual({seat["pool"] for seat in answer["frontier"]["seats"]}, {"anthropic"})

    def test_frontier_agrees_with_assess_for_every_seat(self):
        for author in ("opus-5.5#xhigh", "gpt-6-sol#xhigh", "haiku-5.5#high", "sonnet-5.5#high"):
            answer = frontier_review(ROOT, author)
            for seat in answer["frontier"]["seats"]:
                with self.subTest(author=author, seat=seat["model"]):
                    assessed = assess_review(ROOT, f"{seat['model']}#{seat['effort']}", [author])
                    self.assertEqual(assessed["independence"], "eligible")
                    self.assertEqual(assessed["reviewer"]["review_tier"], answer["frontier"]["review_tier"])

    def test_a_read_below_the_frontier_is_marked_below_and_one_at_it_is_marked_at(self):
        answer = frontier_review(ROOT, "opus-5.5#xhigh", ["gpt-6.1-sol#xhigh", "gpt-6-astra#xhigh"])
        below, at = answer["reads"]
        self.assertEqual((below["standing"], at["standing"]), ("below", "at"))
        for read in answer["reads"]:
            self.assertEqual(read["assessment"]["schema"], "agent-routing-assessment/1")
            self.assertEqual(read["assessment"]["route_version"], answer["route_version"])
            self.assertEqual(read["assessment"]["independence"], "eligible")
        self.assertEqual(below["assessment"]["reviewer"]["model"], "gpt-6.1-sol")

    def test_standing_compares_tiers_and_leaves_eligibility_to_the_assessment(self):
        read, = frontier_review(ROOT, "gpt-6.1-sol#xhigh", ["gpt-6-astra#xhigh"])["reads"]
        self.assertEqual(read["standing"], "above")
        self.assertEqual(read["assessment"]["independence"], "ineligible")

    def test_a_read_that_is_unseated_has_no_standing(self):
        read, = frontier_review(ROOT, "opus-5.5#xhigh", ["sonnet-5.5#high"])["reads"]
        self.assertEqual(read["standing"], "below")
        self.assertEqual(read["assessment"]["qualifiers"], ["same-family", "reviewer-unseated"])

    def test_reads_are_marked_unranked_when_there_is_no_frontier(self):
        root = self.fixture_root()
        path = root / "routing/models.toml"
        path.write_text(path.read_text().replace('  floor = 3\n', '', 1))
        read, = frontier_review(root, "opus-5.5#max", ["gpt-6-astra#xhigh"])["reads"]
        self.assertEqual(read["standing"], "unranked")
        self.assertEqual(read["assessment"]["qualifiers"], ["floor-unknown"])

    def test_an_unknown_author_or_read_is_refused(self):
        for author, reads in (("nonesuch#high", []), ("opus-5.5#xhigh", ["nonesuch#high"]),
                              ("opus-5.5#nonesuch", [])):
            with self.subTest(author=author, reads=reads), self.assertRaises(RouteRefusal) as caught:
                frontier_review(ROOT, author, reads)
            self.assertEqual(caught.exception.kind, "unknown-coordinate")

    def test_an_exhausted_pool_still_marks_the_frontier(self):
        root = self.fixture_root()
        path = root / "routing" / "delegation.toml"
        text = path.read_text()
        marker = 'provider = "openai-codex"\n'
        self.assertIn(marker, text)
        path.write_text(text.replace(marker, marker + 'exhausted = true\n', 1))
        exhausted = frontier_review(root, "opus-5.5#xhigh")
        plain = frontier_review(ROOT, "opus-5.5#xhigh")
        self.assertEqual(exhausted["frontier"], plain["frontier"])

    def test_the_frontier_orders_by_review_tier_and_never_by_pool_rank(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        text = path.read_text()
        start = text.index('id = "gpt-6.1-sol"')
        # A pool rank above every other seat on its pool must not lift a tier-2 seat.
        path.write_text(text[:start] + text[start:].replace('seat_rank = { "openai-codex" = 3 }',
                                                            'seat_rank = { "openai-codex" = 99 }', 1))
        answer = frontier_review(root, "opus-5.5#xhigh")
        self.assertEqual(answer["frontier"]["review_tier"], 3)
        self.assertEqual(self.seats(answer), [("gpt-6-astra", "xhigh", "codex", "openai-codex")])

    def test_a_seat_outside_the_review_profile_never_raises_the_frontier(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        text = path.read_text()
        start = text.index('id = "gpt-6-luna"')
        # Luna max is seated by explore and implement only, never by a review route.
        path.write_text(text[:start] + text[start:].replace('effort = "max"\n  rank = 1',
                                                            'effort = "max"\n  rank = 5', 1))
        self.assertIn("rank = 5", path.read_text())
        answer = frontier_review(root, "opus-5.5#xhigh")
        self.assertEqual(answer["frontier"]["review_tier"], 3)
        self.assertEqual(self.seats(answer), [("gpt-6-astra", "xhigh", "codex", "openai-codex")])

    def test_only_stable_pool_valid_routes_seat_the_frontier(self):
        root = self.fixture_root()
        path = root / "routing" / "profiles.toml"
        text = path.read_text()
        for marker in ('  id = "high-stakes"', '  id = "astra-xhigh"'):
            start = text.index(marker)
            text = text[:start] + text[start:].replace('stability = "stable"', 'stability = "experimental"', 1)
        path.write_text(text)
        answer = frontier_review(root, "opus-5.5#xhigh")
        self.assertEqual(answer["frontier"]["review_tier"], 2)

    def run_cli(self, *args):
        return subprocess.run([ROOT / "bin" / "agent-routing", "frontier", *args], capture_output=True, text=True)

    def test_cli_emits_the_frontier_json_with_reads(self):
        result = self.run_cli("--author", "opus-5.5#xhigh", "--reads", "gpt-6.1-sol#xhigh", "gpt-6-astra#xhigh",
                              "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        answer = json.loads(result.stdout)
        self.assertEqual(answer["schema"], "agent-routing-frontier/1")
        self.assertEqual([read["standing"] for read in answer["reads"]], ["below", "at"])
        self.assertEqual(answer, frontier_review(ROOT, "opus-5.5#xhigh", ["gpt-6.1-sol#xhigh", "gpt-6-astra#xhigh"]))

    def test_cli_prints_a_readable_answer_without_json(self):
        result = self.run_cli("--author", "opus-5.5#xhigh", "--reads", "gpt-6.1-sol#xhigh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("frontier tier 3", result.stdout)
        self.assertIn("gpt-6-astra#xhigh", result.stdout)
        self.assertIn("below", result.stdout)
        unknown = self.run_cli("--author", "opus-5#xhigh")
        self.assertEqual(unknown.returncode, 0, unknown.stderr)
        self.assertIn("frontier tier 3", unknown.stdout)

    def test_the_guide_and_help_list_the_verb_and_state_the_ordering_and_quota_rule(self):
        guide = subprocess.run([ROOT / "bin" / "agent-routing"], capture_output=True, text=True).stdout
        self.assertIn("agent-routing frontier --author", guide)
        self.assertIn("agent-routing-frontier/1", guide)
        verb_help = self.run_cli("--help").stdout
        self.assertIn("review_tier", verb_help)
        self.assertIn("not inputs", verb_help)
        usage = subprocess.run([ROOT / "bin" / "agent-routing", "help"], capture_output=True, text=True).stdout
        self.assertIn("frontier --author", usage)

    def test_cli_refuses_an_unknown_coordinate_with_a_payload(self):
        result = self.run_cli("--author", "nonesuch#high", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr.splitlines()[-1])["kind"], "unknown-coordinate")


class RankLintTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        shutil.copytree(ROOT / "routing", root / "routing")
        return root

    def rewrite(self, root, name, old, new):
        path = root / "routing" / name
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def problems(self, root):
        return validation_problems(root)

    def test_the_shipped_ranks_and_sources_are_valid(self):
        self.assertEqual(self.problems(ROOT), [])

    def test_a_seated_tier_without_a_rank_is_reported(self):
        root = self.fixture_root()
        self.rewrite(root, "models.toml", '  seat_rank = { "openai-codex" = 3 }\n', "")
        self.assertIn(
            "model 'gpt-6.1-sol' effort 'xhigh': seated on pool 'openai-codex' without a seat_rank",
            self.problems(root),
        )

    def test_a_rank_on_an_unseated_tier_is_reported(self):
        root = self.fixture_root()
        self.rewrite(
            root,
            "models.toml",
            '  effort = "low"\n  rank = 2\n  floor = 2\n  use = "uncalibrated; unrouted. Operator evidence',
            '  effort = "low"\n  rank = 2\n  floor = 2\n  seat_rank = { "openai-codex" = 3 }\n  use = "uncalibrated; unrouted. Operator evidence',
        )
        self.assertIn("model 'gpt-6-astra' effort 'low': seat_rank on a tier no stable route seats", self.problems(root))

    def test_a_boolean_rank_is_reported(self):
        root = self.fixture_root()
        self.rewrite(root, "models.toml", '  seat_rank = { "openai-codex" = 3 }\n', '  seat_rank = { "openai-codex" = true }\n')
        self.assertTrue(any("must be a positive integer, not True" in problem for problem in self.problems(root)))

    def test_a_rank_falling_along_the_effort_order_is_reported(self):
        root = self.fixture_root()
        self.rewrite(root, "models.toml", '  seat_rank = { "openai-codex" = 5 }\n', '  seat_rank = { "openai-codex" = 3 }\n')
        self.assertIn(
            "model 'gpt-6-astra' pool 'openai-codex': seat_rank falls from medium (4) to xhigh (3)",
            self.problems(root),
        )

    def test_a_score_inversion_is_reported(self):
        root = self.fixture_root()
        self.rewrite(root, "models.toml", '  seat_rank = { "openai-codex" = 1 }\n', '  seat_rank = { "openai-codex" = 1 }\n  pass_at_1 = 0.9\n')
        self.rewrite(root, "models.toml", '  seat_rank = { "openai-codex" = 2 }\n', '  seat_rank = { "openai-codex" = 2 }\n  pass_at_1 = 0.5\n')
        self.assertTrue(
            any("scores 0.9 above" in problem and "holds the lower rank" in problem for problem in self.problems(root))
        )

    def test_an_unknown_escalation_source_names_the_profile(self):
        root = self.fixture_root()
        self.rewrite(root, "profiles.toml", 'escalation_sources = ["execute"]', 'escalation_sources = ["exeucte"]')
        problems = self.problems(root)
        self.assertIn("implement: escalation source 'exeucte' is not a profile", problems)
        self.assertFalse(any("unknown key" in problem for problem in problems))

    def test_a_tier_seated_by_an_undeclared_provider_is_ranked_under_its_name(self):
        root = self.fixture_root()
        self.rewrite(
            root,
            "profiles.toml",
            '[[profile]]\nid = "generate"',
            '  [[profile.variant]]\n  id = "unpooled"\n'
            '  provider = "deepseek"\n  model = "deepseek-flash"\n  effort = "max"\n'
            '  stability = "stable"\n  backends = ["pi"]\n\n[[profile]]\nid = "generate"',
        )
        self.assertIn(
            "model 'deepseek-flash' effort 'max': seated on pool 'deepseek' without a seat_rank",
            self.problems(root),
        )
        self.rewrite(
            root, "models.toml",
            '  seat_rank = { "opencode-go" = 1 }\n  predecessor = "V4 Flash 0731"',
            '  seat_rank = { "opencode-go" = 1, "deepseek" = 1 }\n  predecessor = "V4 Flash 0731"',
        )
        self.assertEqual(self.problems(root), [])

    def test_a_duplicate_model_id_is_reported(self):
        root = self.fixture_root()
        path = root / "routing" / "models.toml"
        path.write_text(path.read_text() + '\n[[model]]\nid = "gpt-6-sol"\nfamily = "openai"\nrole = "duplicate"\n')
        self.assertIn("duplicate model 'gpt-6-sol'", self.problems(root))

    def test_a_valid_escalation_source_passes(self):
        root = self.fixture_root()
        self.rewrite(root, "profiles.toml", 'escalation_sources = ["execute"]', 'escalation_sources = ["execute", "plan"]')
        self.assertEqual(self.problems(root), [])


if __name__ == "__main__":
    unittest.main()

class FableAuthorFloorTest(unittest.TestCase):
    def test_each_fable_effort_has_its_own_author_requirement(self):
        for effort, floor in {"low": 1, "medium": 1, "high": 2, "xhigh": 2, "max": 3}.items():
            with self.subTest(effort=effort):
                author = f"fable-5.1#{effort}"
                assessment = assess_review(ROOT, "gpt-6.1-sol#xhigh", [author])
                self.assertEqual(assessment["floor"], floor)
                self.assertEqual(assessment["qualifiers"], ["below-floor"] if floor == 3 else [])
                self.assertEqual(resolve(ROOT, "review", "codex", author=author)["review"]["author_tier"], floor)
                self.assertIn("reviewer-unseated", assess_review(ROOT, author, ["gpt-6-luna#max"])["qualifiers"])
                with self.assertRaises(RouteRefusal):
                    resolve(ROOT, "review", "claude", author=author)

    def test_bare_fable_uses_its_highest_floor(self):
        self.assertEqual(assess_review(ROOT, "gpt-6.1-sol#xhigh", ["fable-5.1"])["floor"], 3)
        self.assertEqual(resolve(ROOT, "review", "codex", author="fable-5.1")["review"]["author_tier"], 3)

    def test_mimo_and_muse_floors_are_known_without_a_route(self):
        for model in ("mimo-v2.6-flash", "mimo-v2.6-pro", "muse-spark-1.2", "muse-spark-1.3"):
            with self.subTest(model=model):
                answer = assess_review(ROOT, "gpt-6.1-sol#xhigh", [model])
                self.assertEqual(answer["floor"], 1)
                self.assertTrue(answer["clears"])
