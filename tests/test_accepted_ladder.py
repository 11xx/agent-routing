"""Only an accepted first-parent table can supply a dated capability version."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import review_ladder as ladder
from routing_profiles import assess_review


class AcceptedLadderTest(unittest.TestCase):
    def setUp(self):
        cache = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "agent-routing/tests"
        cache.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=cache, prefix="accepted-ladder-")
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.git("init", "--initial-branch=master")
        self.git("commit", "--allow-empty", "-m", "test: establish pre-numeric history",
                 date="2026-10-06T00:00:00Z")
        (self.root / "routing").mkdir()
        (self.root / "eras").mkdir()
        self.models(2)
        for name in ("profiles", "delegation"):
            (self.root / f"routing/{name}.toml").write_text("# fixture manifest\n")
        (self.root / ladder.EVIDENCE).write_text("Accepted reconstruction evidence.\n")
        self.base = self.commit("2026-10-07T00:00:00Z", "test: establish the accepted table")
        numeric_start = patch.object(ladder, "NUMERIC_START", self.base)
        numeric_start.start()
        self.addCleanup(numeric_start.stop)

    def git(self, *args, date=None):
        env = dict(os.environ)
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        result = subprocess.run(["git", "-C", str(self.root), "-c", "commit.gpgsign=false", *args],
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit(self, date, message):
        self.git("add", ".")
        self.git("commit", "-m", message, date=date)
        return self.git("rev-parse", "HEAD")

    def models(self, rank):
        text = "[review]\nclearance = 2\n"
        for name, family, value in (("fixture-reviewer", "a", rank),
                                    ("fixture-author", "b", 2), ("fixture-peer", "c", 3)):
            text += f'''\n[[model]]
id = "{name}"
family = "{family}"
[[model.effort]]
effort = "high"
rank = {value}
floor = 2
'''
        (self.root / "routing/models.toml").write_text(text)

    def branch_table(self, rank=1):
        self.git("checkout", "-b", "proposal")
        self.models(rank)
        return self.commit("2026-10-08T00:00:00Z", "test: propose an unaccepted table")

    def assess(self, instant="2026-10-09T00:00:00Z", **kwargs):
        return assess_review(self.root, "fixture-reviewer#high", ["fixture-author#high"],
                             as_of=instant, **kwargs)

    def cli(self, *args):
        scripts = self.root / "bin"
        if not scripts.exists():
            scripts.mkdir()
            for name in ("agent-routing", "assess-review", "review-ladder"):
                shutil.copy2(ROOT / "bin" / name, scripts / name)
            (self.root / "lib").symlink_to(ROOT / "lib", target_is_directory=True)
            # Resolve the CLI's numeric-history boundary inside the fixture repository.
            self.git("tag", "dc54196", self.base)
        return subprocess.run([scripts / "agent-routing", *args], text=True, capture_output=True)

    def assert_cli_refuses_non_increasing_dates(self, date):
        self.models(1)
        self.commit("2026-10-10T00:00:00Z", "test: accept a later table")
        self.models(3)
        rejected = self.commit(date, "test: accept a table without advancing time")
        reason = f"version 'v-{rejected}': effective_from must increase"
        exported = self.cli("ladder", "--json", "--history")
        self.assertNotEqual(exported.returncode, 0)
        self.assertEqual(exported.stdout, "")
        self.assertIn(reason, exported.stderr)
        for instant in ("2026-10-09T00:00:00Z", "2026-10-07T12:00:00Z", "2026-10-11T00:00:00Z"):
            with self.subTest(instant=instant):
                answer = self.cli("assess", "--reviewer", "fixture-reviewer#high",
                                  "--author", "fixture-author#high", "--as-of", instant, "--json")
                self.assertNotEqual(answer.returncode, 0, answer.stdout)
                self.assertEqual(answer.stdout, "")
                self.assertIn(reason, answer.stderr)

    def test_dated_cli_refuses_backward_capability_dates_like_history_export(self):
        self.assert_cli_refuses_non_increasing_dates("2026-10-08T00:00:00Z")

    def test_dated_cli_refuses_equal_capability_dates_like_history_export(self):
        self.assert_cli_refuses_non_increasing_dates("2026-10-10T00:00:00Z")

    def test_dated_cli_and_export_accept_increasing_capability_dates(self):
        self.models(1)
        self.commit("2026-10-10T00:00:00Z", "test: accept a later table")
        self.models(3)
        self.commit("2026-10-11T00:00:00Z", "test: accept another later table")
        exported = self.cli("ladder", "--json", "--history")
        self.assertEqual(exported.returncode, 0, exported.stderr)
        for instant, rank in (("2026-10-09T00:00:00Z", 2), ("2026-10-10T00:00:00Z", 1),
                              ("2026-10-11T00:00:00Z", 3)):
            with self.subTest(instant=instant):
                answer = self.cli("assess", "--reviewer", "fixture-reviewer#high",
                                  "--author", "fixture-author#high", "--as-of", instant, "--json")
                self.assertEqual(answer.returncode, 0, answer.stderr)
                self.assertEqual(json.loads(answer.stdout)["reviewer"]["review_tier"], rank)

    def test_dated_cli_and_export_accept_equal_dates_without_a_capability_change(self):
        self.models(1)
        self.commit("2026-10-08T00:00:00Z", "test: accept a later table")
        manifest = self.root / "routing/models.toml"
        manifest.write_text(manifest.read_text() + "\n# capability-neutral metadata\n")
        self.commit("2026-10-08T00:00:00Z", "test: record capability-neutral metadata")
        exported = self.cli("ladder", "--json", "--history")
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertEqual(len(json.loads(exported.stdout)["version"]), 3)
        answer = self.cli("assess", "--reviewer", "fixture-reviewer#high",
                          "--author", "fixture-author#high", "--as-of", "2026-10-08T00:00:00Z", "--json")
        self.assertEqual(answer.returncode, 0, answer.stderr)
        self.assertEqual(json.loads(answer.stdout)["reviewer"]["review_tier"], 1)

    def assert_cli_matches_exported_intervals(self, version, instants):
        exported = self.cli("ladder", "--json", "--history", "--accepted", "master")
        self.assertEqual(exported.returncode, 0, exported.stderr)
        versions = json.loads(exported.stdout)["version"]
        self.assertEqual([row["id"] for row in versions],
                         ["gap-2026-08-01", f"v-{self.base}", f"v-{version}"])
        self.assertEqual(versions[-1]["effective_from"], "2026-10-10T00:00:00Z")
        for instant in instants:
            with self.subTest(instant=instant):
                active = [row for row in versions
                          if ladder.instant(row["effective_from"]) <= ladder.instant(instant)][-1]
                reviewer = next(row for row in active["model"] if row["model"] == "fixture-reviewer")
                rank = reviewer["efforts"][0]["rank"]
                answer = self.cli("assess", "--reviewer", "fixture-reviewer#high",
                                  "--author", "fixture-author#high", "--as-of", instant,
                                  "--accepted", "master", "--json")
                self.assertEqual(answer.returncode, 0, answer.stderr)
                assessment = json.loads(answer.stdout)
                self.assertEqual(assessment["reviewer"]["review_tier"], rank)
                self.assertEqual(assessment["clears"], rank >= 2)

    def test_dated_cli_matches_export_before_a_version_with_a_backdated_neutral_descendant(self):
        self.models(1)
        version = self.commit("2026-10-10T00:00:00Z", "test: accept a later table")
        (self.root / "note.txt").write_text("Capability-neutral evidence.\n")
        self.commit("2026-10-08T00:00:00Z", "test: record a backdated neutral descendant")
        self.assert_cli_matches_exported_intervals(version, (
            "2026-10-07T12:00:00Z", "2026-10-08T00:00:00Z", "2026-10-09T00:00:00Z",
            "2026-10-09T23:59:59.999999Z", "2026-10-10T00:00:00Z", "2026-10-11T00:00:00Z",
        ))

    def test_dated_cli_matches_export_after_a_version_with_a_future_dated_neutral_parent(self):
        (self.root / "note.txt").write_text("Capability-neutral evidence.\n")
        self.commit("2026-10-12T00:00:00Z", "test: record future-dated neutral evidence")
        self.models(1)
        version = self.commit("2026-10-10T00:00:00Z", "test: accept a table after neutral evidence")
        self.assert_cli_matches_exported_intervals(version, (
            "2026-10-09T00:00:00Z", "2026-10-10T00:00:00Z", "2026-10-11T00:00:00Z",
            "2026-10-12T00:00:00Z", "2026-10-13T00:00:00Z",
        ))

    def test_branch_only_table_never_appears_in_default_accepted_history(self):
        proposal = self.branch_table()
        versions = ladder.export(self.root, history=True)["version"]
        self.assertEqual([v["id"] for v in versions], ["gap-2026-08-01", f"v-{self.base}"])
        self.assertNotIn(f"v-{proposal}", [v["id"] for v in versions])

    def test_current_export_reads_the_accepted_ref_instead_of_branch_or_working_table(self):
        self.branch_table()
        self.models(3)
        version, = ladder.export(self.root)["version"]
        self.assertEqual(version["id"], f"v-{self.base}")
        reviewer = next(m for m in version["model"] if m["model"] == "fixture-reviewer")
        self.assertEqual(reviewer["efforts"][0]["rank"], 2)

    def test_as_of_does_not_use_a_branch_table_before_acceptance(self):
        self.branch_table()
        answer = self.assess()
        self.assertEqual(answer["reviewer"]["review_tier"], 2)
        self.assertTrue(answer["clears"])

    def test_no_ff_merge_dates_the_table_at_acceptance_and_hides_intermediate_tables(self):
        intermediate = self.branch_table()
        self.models(3)
        proposed = self.commit("2026-10-08T01:00:00Z", "test: correct the proposed table")
        self.git("checkout", "master")
        self.git("merge", "--no-ff", "proposal", "-m", "test: accept the corrected table",
                 date="2026-10-10T00:00:00Z")
        accepted = self.git("rev-parse", "master")
        self.git("checkout", "proposal")
        versions = ladder.export(self.root, history=True)["version"]
        self.assertEqual([v["id"] for v in versions],
                         ["gap-2026-08-01", f"v-{self.base}", f"v-{accepted}"])
        self.assertEqual(versions[-1]["effective_from"], "2026-10-10T00:00:00Z")
        self.assertNotIn(f"v-{intermediate}", [v["id"] for v in versions])
        self.assertNotIn(f"v-{proposed}", [v["id"] for v in versions])
        self.assertEqual(self.assess()["reviewer"]["review_tier"], 2)
        self.assertEqual(self.assess("2026-10-10T00:00:00Z")["reviewer"]["review_tier"], 3)

    def test_explicit_accepted_ref_selects_the_same_history_for_export_and_assessment(self):
        self.git("branch", "accepted-copy")
        self.models(1)
        self.commit("2026-10-08T00:00:00Z", "test: advance a different accepted ref")
        version, = ladder.export(self.root, accepted="accepted-copy")["version"]
        self.assertEqual(version["id"], f"v-{self.base}")
        self.assertEqual(self.assess(accepted="accepted-copy")["reviewer"]["review_tier"], 2)

    def test_remote_default_branch_metadata_selects_the_local_default_ref(self):
        self.git("branch", "main")
        self.git("update-ref", "refs/remotes/origin/main", self.base)
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        self.models(1)
        self.commit("2026-10-08T00:00:00Z", "test: advance the nondefault branch")
        version, = ladder.export(self.root)["version"]
        self.assertEqual(version["id"], f"v-{self.base}")
        self.assertEqual(self.assess()["reviewer"]["review_tier"], 2)

    def test_a_capability_neutral_commit_does_not_redate_the_current_version(self):
        manifest = self.root / "routing/models.toml"
        manifest.write_text(manifest.read_text() + "\n# capability-neutral metadata\n")
        self.commit("2026-10-08T00:00:00Z", "test: record capability-neutral metadata")
        version, = ladder.export(self.root)["version"]
        self.assertEqual((version["id"], version["effective_from"]),
                         (f"v-{self.base}", "2026-10-07T00:00:00Z"))

    def test_historical_witness_ignores_working_and_later_committed_era_edits(self):
        before = self.assess("2026-10-07T01:00:00Z")
        (self.root / ladder.EVIDENCE).write_text("Unaccepted evidence.\n")
        self.assertEqual(self.assess("2026-10-07T01:00:00Z"), before)
        self.commit("2026-10-08T00:00:00Z", "test: accept later evidence")
        self.assertEqual(self.assess("2026-10-07T01:00:00Z"), before)

    def test_a_missing_historical_era_file_is_witnessed_without_a_working_tree_fallback(self):
        self.git("rm", ladder.EVIDENCE)
        self.commit("2026-10-08T00:00:00Z", "test: record a revision without era evidence")
        before = self.assess()
        (self.root / "eras").mkdir(exist_ok=True)
        (self.root / ladder.EVIDENCE).write_text("Working-only evidence.\n")
        self.assertEqual(self.assess(), before)

    def test_legacy_answers_follow_current_reconstruction_and_witness_the_projected_table(self):
        manifest = self.root / "routing/models.toml"
        manifest.write_text(manifest.read_text().replace("rank =", "review_tier =").replace("floor =", "author_floor ="))
        self.commit("2026-10-08T00:00:00Z", "test: establish a legacy table")
        before = self.assess()
        original = ladder.project

        def reconstructed(*args, **kwargs):
            models = original(*args, **kwargs)
            next(m for m in models if m["model"] == "fixture-reviewer")["efforts"][0]["rank"] = 3
            return models

        with patch.object(ladder, "project", side_effect=reconstructed):
            after = self.assess()
        self.assertEqual((before["reviewer"]["review_tier"], after["reviewer"]["review_tier"]), (2, 3))
        self.assertNotEqual(before["route_version"], after["route_version"])


class AcceptedLadderCliTest(unittest.TestCase):
    def test_current_export_does_not_invent_a_table_for_a_pre_numeric_accepted_ref(self):
        with self.assertRaisesRegex(ValueError, "ladder-gap"):
            ladder.export(ROOT, accepted="dc54196^")


if __name__ == "__main__":
    unittest.main()
