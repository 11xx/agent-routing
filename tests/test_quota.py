import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from quota_routing import admit_review
from routing_profiles import RouteRefusal, resolve, validation_problems

NOW = 2_000_000_000


def window(remaining):
    return dict(used_percentage=100 - remaining, remaining_percentage=remaining, resets_at=NOW + 3600)


def usage(codex=60, claude=60):
    return {key: dict(state="fresh", updated_at=NOW - 10, five_hour=window(value), seven_day=window(80))
            for key, value in (("codex", codex), ("claude", claude))}


class QuotaAdmissionTest(unittest.TestCase):
    def review(self, observed, author="gpt-6.1-sol#xhigh"):
        return admit_review(ROOT, author, observed, "a" * 40, "b" * 40, now=NOW)

    def test_codex_review_threshold_and_unknown_return_debt_without_a_route(self):
        allowed = self.review(usage(claude=51))
        self.assertEqual(allowed["status"], "route")
        route = allowed["route"]
        self.assertEqual((route["backend"], route["provider"], route["model"], route["effort"]),
                         ("claude", "anthropic", "claude-opus-5-5", "xhigh"))
        self.assertEqual(route["review"]["independence"], "eligible")
        self.assertEqual(allowed["execution"]["access"], "read-only")
        self.assertFalse(allowed["execution"]["persist_session"])
        self.assertEqual(allowed["execution"]["range"], "a" * 40 + ".." + "b" * 40)
        for observed in (usage(claude=50), usage(claude=49), usage(claude=0), {}):
            answer = self.review(observed)
            self.assertEqual(answer["status"], "review-debt")
            self.assertIsNone(answer["route"])
            self.assertEqual(answer["debt_kind"], "independent-review")

    def test_stale_inconsistent_and_expired_observations_are_unknown(self):
        for field, value in (("state", "stale"), ("state", "disabled"), ("updated_at", NOW - 301),
                             ("updated_at", NOW + 1), ("five_hour", None),
                             ("five_hour", dict(remaining_percentage=90, used_percentage=5, resets_at=NOW + 50)),
                             ("five_hour", dict(remaining_percentage=True, used_percentage=99, resets_at=NOW + 50)),
                             ("five_hour", dict(remaining_percentage=90, used_percentage=10, resets_at=NOW))):
            with self.subTest(field=field, value=value):
                observed = usage()
                observed["claude"][field] = value
                self.assertEqual(self.review(observed)["reason"], "pool-unknown")

    def test_a_pool_is_measured_by_the_windows_its_plan_has(self):
        # Codex Pro has no five-hour window, so a weekly-only snapshot is a
        # complete measurement there; Claude's plan has both, so the same
        # snapshot shape leaves Claude unmeasured.
        observed = usage()
        del observed["codex"]["five_hour"]
        route = self.review(observed, "opus-5.5#xhigh")
        self.assertEqual(route["status"], "route")
        self.assertEqual(route["quota"]["windows"], {"seven_day": {"remaining_percentage": 80,
                                                                   "resets_at": NOW + 3600}})
        observed["codex"]["seven_day"] = window(0)
        self.assertEqual(self.review(observed, "opus-5.5#xhigh")["reason"], "pool-exhausted")
        del observed["codex"]["seven_day"]
        self.assertEqual(self.review(observed, "opus-5.5#xhigh")["reason"], "pool-unknown")
        observed = usage()
        del observed["claude"]["five_hour"]
        self.assertEqual(self.review(observed)["reason"], "pool-unknown")

    def test_a_measured_pool_must_declare_its_windows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            shutil.copytree(ROOT / "routing", root / "routing")
            delegation = root / "routing/delegation.toml"
            text = delegation.read_text()
            delegation.write_text(text.replace('windows = ["seven_day"]\n', "", 1))
            self.assertIn("pools: openai-codex must declare the windows its plan has (five_hour, seven_day)",
                          validation_problems(root))
            delegation.write_text(text.replace('windows = ["seven_day"]', 'windows = ["daily"]', 1))
            self.assertTrue(any("openai-codex must declare" in problem for problem in validation_problems(root)))

    def test_a_reported_window_the_plan_does_not_declare_still_counts(self):
        observed = usage()
        observed["codex"]["five_hour"] = window(0)
        self.assertEqual(self.review(observed, "opus-5.5#xhigh")["reason"], "pool-exhausted")
        observed["codex"]["five_hour"] = dict(remaining_percentage=90, used_percentage=5, resets_at=NOW + 50)
        self.assertEqual(self.review(observed, "opus-5.5#xhigh")["reason"], "pool-unknown")

    def test_weekly_exhaustion_blocks_an_otherwise_healthy_window(self):
        observed = usage()
        observed["claude"]["seven_day"] = window(0)
        self.assertEqual(self.review(observed)["reason"], "pool-exhausted")

    def test_opus_authored_review_keeps_an_independent_codex_route(self):
        route = self.review(usage(claude=0), "opus-5.5#xhigh")["route"]
        self.assertEqual((route["backend"], route["model"]), ("codex", "gpt-6.1-sol"))
        self.assertEqual(route["review"]["independence"], "eligible")
        answer = self.review(usage(), "not-a-model#high")
        self.assertEqual(answer["status"], "review-debt")
        self.assertIsNone(answer["route"])

    def test_execute_fallbacks_are_bidirectional_and_record_the_skipped_route(self):
        for backend, observed, alternative in (("codex", usage(codex=0), "claude"),
                                                ("claude", usage(claude=0), "codex")):
            route = resolve(ROOT, "execute", backend, usage=observed, now=NOW)
            self.assertEqual(route["backend"], alternative)
            self.assertEqual(route["rerouted_from"]["backend"], backend)
            self.assertEqual(route["rerouted_from"]["reason"], "pool-exhausted")
        original = resolve(ROOT, "execute", "codex")
        route = resolve(ROOT, "execute", "codex", usage=usage(), now=NOW)
        self.assertEqual({key: route[key] for key in original}, original)
        self.assertNotIn("rerouted_from", route)

    def test_refusals_are_bounded_and_do_not_change_pinned_or_unconfigured_routes(self):
        cases = [("execute", "codex", usage(0, 0), None, "pool-exhausted"),
                 ("execute", "claude", usage(claude=0), "opus", "pool-exhausted"),
                 ("implement", "codex", usage(codex=0), None, "pool-exhausted"),
                 ("execute", "codex", {}, None, "quota-unknown")]
        for profile, backend, observed, variant, kind in cases:
            with self.subTest(profile=profile, backend=backend, variant=variant):
                with self.assertRaises(RouteRefusal) as caught:
                    resolve(ROOT, profile, backend, usage=observed, now=NOW, variant_id=variant)
                self.assertEqual(caught.exception.kind, kind)
        observed = usage(codex=0)
        observed["claude"]["state"] = "unavailable"
        with self.assertRaises(RouteRefusal) as caught:
            resolve(ROOT, "execute", "codex", usage=observed, now=NOW)
        self.assertEqual(len(caught.exception.payload()["skipped_routes"]), 2)

    def test_fallback_caller_advice_names_the_returned_and_skipped_seats(self):
        route = resolve(ROOT, "execute", "codex", usage=usage(codex=0), now=NOW,
                        caller="gpt-6.1-sol#xhigh", caller_provider="openai-codex")
        self.assertEqual(route["confirmation"]["selection"]["model"], route["model"])
        self.assertEqual(route["confirmation"]["pool_comparison"], "scarcer")
        self.assertEqual(route["rerouted_from"]["confirmation"]["pool_comparison"], "same")

    def test_cli_reads_only_supplied_snapshots_and_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "usage.json"
            observed = usage()
            for observation in observed.values():
                observation["updated_at"] = int(time.time())
                for name in ("five_hour", "seven_day"):
                    observation[name]["resets_at"] = int(time.time()) + 3600
            path.write_text(json.dumps(observed))
            result = subprocess.run([ROOT / "bin/agent-routing", "admit-review", "--author", "gpt-6.1-sol#xhigh",
                                     "--usage-file", path, "--base", "a" * 40, "--head", "b" * 40, "--json"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "route")
            observed["claude"]["five_hour"].update(remaining_percentage=50, used_percentage=50)
            path.write_text(json.dumps(observed))
            result = subprocess.run([ROOT / "bin/admit-review", "--author", "gpt-6.1-sol#xhigh",
                                     "--usage-file", path, "--base", "a" * 40, "--head", "b" * 40, "--json"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "review-debt")
            observed["codex"]["five_hour"].update(remaining_percentage=0, used_percentage=100)
            path.write_text(json.dumps(observed))
            result = subprocess.run([ROOT / "bin/resolve-route", "execute", "--backend", "codex",
                                     "--usage-file", path, "--json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["rerouted_from"]["reason"], "pool-exhausted")
            path.write_text("null")
            result = subprocess.run([ROOT / "bin/admit-review", "--author", "gpt-6.1-sol#xhigh",
                                     "--usage-file", path, "--base", "a" * 40, "--head", "b" * 40, "--json"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "review-debt")
            self.assertIsNone(json.loads(result.stdout)["route"])
            result = subprocess.run([ROOT / "bin/resolve-route", "execute", "--backend", "codex",
                                     "--usage-file", path, "--json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr)["kind"], "invalid-usage")

    def test_policy_rejects_unstable_fallback_and_invalid_threshold(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            shutil.copytree(ROOT / "routing", root / "routing")
            path = root / "routing/profiles.toml"
            source = path.read_text()
            path.write_text(source.replace('variant = "opus"', 'variant = "missing"'))
            self.assertTrue(any("fallback must name a stable route" in problem for problem in validation_problems(root)))
            path.write_text(source.replace("claude_minimum_remaining = 50", "claude_minimum_remaining = true"))
            self.assertTrue(any("threshold" in problem for problem in validation_problems(root)))
