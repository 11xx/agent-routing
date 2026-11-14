"""The capability ladder read from Git history, over a scratch repository of the fixture data."""

import os
import re
import subprocess
import unittest
from unittest import mock

from fixture import edit, scratch

import review_ladder
import stores
from routing_profiles import RouteRefusal, assess_review

HIGH = 'model = "nw-atlas-2"\neffort = "high"\nrank = 2'
RAISED = 'model = "nw-atlas-2"\neffort = "high"\nrank = 3'

IDENTITY = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@localhost",
            "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@localhost"}


class LadderCase(unittest.TestCase):
    """A scratch repository whose first data commit is the numeric record's start."""

    def setUp(self):
        self.root = scratch(self)
        self.git("init", "--quiet", "--initial-branch=main")
        (self.root / "README.md").write_text("fixture\n")
        self.git("add", "README.md")
        self.commit("2030-01-02T00:00:00Z")
        self.git("add", "--all")
        self.first = self.commit("2030-01-03T00:00:00Z")
        patcher = mock.patch.object(review_ladder, "NUMERIC_START", self.first)
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, *args, date=None):
        environment = {**os.environ, **IDENTITY}
        if date:
            environment.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        return subprocess.run(["git", "-C", str(self.root), "-c", "commit.gpgsign=false", *args],
                              capture_output=True, text=True, check=True, env=environment).stdout.strip()

    def commit(self, date):
        self.git("commit", "--quiet", "--all", "--message", f"data at {date}", date=date)
        return self.git("rev-parse", "HEAD")

    def tier(self, as_of, **options):
        """nw-atlas-2#high's review tier as the dated assessment reads it."""
        answer = assess_review(self.root, "nw-atlas-2#high", ["ts-3-core#max"], as_of=as_of, **options)
        return answer["reviewer"]["review_tier"]


class LadderTest(LadderCase):
    def test_the_current_version_is_the_first_commit_of_the_current_table(self):
        """Claim: the current version is named for the earliest accepted commit
        whose table is unchanged, its rows carry the lab, identities and tiers
        from the stores, and a change to notes or policy alone keeps it.
        Rejects a version that moves on commits the table does not see."""
        with (self.root / stores.NOTES).open("a") as notes:
            notes.write(stores.emit_note({"id": "n0003", "date": "2030-01-06", "model": "orbit-flash",
                                          "kind": "observation", "areas": ["latency"], "claim": "Fast.",
                                          "cause": "unknown", "evidence": "fixture"}))
        edit(self.root, stores.POLICY, "clearance = 2", "clearance = 3")
        self.commit("2030-01-04T00:00:00Z")
        version = review_ladder.export(self.root, accepted="HEAD")["version"][0]
        self.assertEqual((version["id"], version["source"]),
                         (f"v-{self.first}", f"agent-routing data/catalog.toml at {self.first}"))
        atlas = next(row for row in version["model"] if row["model"] == "nw-atlas-2")
        self.assertEqual((atlas["family"], atlas["identities"], atlas["superseded"]),
                         ("northwind", ["claude-atlas-2", "northwind-atlas-2", "nw-atlas-2"], False))
        self.assertIn({"effort": "xhigh", "rank": 3, "floor": 2}, atlas["efforts"])

    def test_history_adds_a_version_when_a_tier_changes(self):
        """Claim: --history opens with the declared gap and adds a version at
        each accepted commit that changes the table. Rejects a history that
        drops a change or repeats an unchanged table."""
        edit(self.root, stores.CATALOG, 'model = "nw-swift-2"\neffort = "max"\nrank = 1',
             'model = "nw-swift-2"\neffort = "max"\nrank = 2')
        second = self.commit("2030-01-05T00:00:00Z")
        versions = review_ladder.export(self.root, history=True, accepted="HEAD")["version"]
        self.assertEqual([version["gap"] for version in versions], [True, False, False])
        self.assertEqual([version.get("id") for version in versions[1:]], [f"v-{self.first}", f"v-{second}"])
        self.assertEqual(versions[2]["effective_from"], "2030-01-05T00:00:00Z")

    def test_version_dates_must_increase(self):
        """Claim: a ladder whose versions repeat or reverse an effective_from
        instant is refused. Rejects two tables in force at one instant, or a
        history that runs backwards."""
        ladder = review_ladder.export(self.root, history=True)
        gap, table = ladder["version"]
        review_ladder.validate(ladder)
        for instant in (gap["effective_from"], "2000-01-01T00:00:00Z"):
            with self.subTest(instant=instant):
                broken = {**ladder, "version": [gap, {**table, "effective_from": instant}]}
                with self.assertRaisesRegex(ValueError, "effective_from must increase"):
                    review_ladder.validate(broken)


class DatedAssessmentTest(LadderCase):
    def test_a_dated_assessment_reads_the_table_in_force_then(self):
        """Claim: --as-of judges with the capability table of the last
        accepted commit at that instant, not today's. Rejects a past review
        re-judged by a later rank change."""
        edit(self.root, stores.CATALOG, HIGH, RAISED)
        self.commit("2030-01-05T00:00:00Z")
        self.assertEqual((self.tier("2030-01-04T00:00:00Z"), self.tier("2030-01-06T00:00:00Z")), (2, 3))

    def test_dated_answers_keep_each_purpose_and_refuse_exhaustive(self):
        """Claim: a dated assessment answers clearance and findings from the
        table in force then, identically whichever is asked, and refuses
        exhaustive, which selects a reader rather than judging a read.
        Rejects a purpose changing a dated answer it does not own."""
        edit(self.root, stores.CATALOG, HIGH, RAISED)
        self.commit("2030-01-05T00:00:00Z")
        for purpose in ("clearance", "findings"):
            with self.subTest(purpose=purpose):
                before = assess_review(self.root, "nw-atlas-2#high", ["ts-3-core#max", "orbit-flash#max"],
                                       as_of="2030-01-04T00:00:00Z", purpose=purpose)
                after = assess_review(self.root, "nw-atlas-2#high", ["ts-3-prime#xhigh", "orbit-flash#max"],
                                      as_of="2030-01-06T00:00:00Z", purpose=purpose)
                self.assertEqual([(answer["reviewer"]["review_tier"], answer["floor"], answer["findings"],
                                   answer["clears"], answer["qualifiers"]) for answer in (before, after)],
                                 [(2, 1, "eligible", True, []), (3, 2, "eligible", True, [])])
        with self.assertRaises(RouteRefusal) as caught:
            assess_review(self.root, "nw-atlas-2#high", ["nw-swift-2#high"], as_of="2030-01-06T00:00:00Z",
                          purpose="exhaustive")
        self.assertEqual(caught.exception.kind, "invalid-purpose")

    def test_malformed_and_pre_record_instants_are_refused(self):
        """Claim: an instant that is not RFC 3339, and one before the numeric
        record, are refused as historical-ladder without an answer, and
        --accepted needs --as-of. Rejects a dated answer read from the wrong
        table or none."""
        for instant, message in (("2030-13-01T00:00:00Z", "expected an RFC 3339 instant"),
                                 ("2030-01-04", "expected an RFC 3339 instant"),
                                 ("2029-12-31T00:00:00Z", "ladder-gap")):
            with self.subTest(instant=instant):
                with self.assertRaises(RouteRefusal) as caught:
                    self.tier(instant)
                self.assertEqual(caught.exception.kind, "historical-ladder")
                self.assertIn(message, str(caught.exception))
        with self.assertRaises(RouteRefusal) as caught:
            assess_review(self.root, "nw-atlas-2#high", ["ts-3-core#max"], accepted="main")
        self.assertEqual(caught.exception.kind, "invalid-accepted")

    def test_the_accepted_ref_selects_the_history_for_export_and_assessment(self):
        """Claim: asked from a feature checkout, a table committed only on
        that branch is absent from the default accepted history, which is the
        default branch, and present when the branch is named, for both the
        export and the dated assessment. Rejects reading HEAD, a branch or the
        working tree as accepted."""
        self.git("checkout", "--quiet", "-b", "feature")
        edit(self.root, stores.CATALOG, HIGH, RAISED)
        branch = self.commit("2030-01-05T00:00:00Z")
        edit(self.root, stores.CATALOG, RAISED, 'model = "nw-atlas-2"\neffort = "high"\nrank = 1')
        self.assertEqual((self.git("rev-parse", "HEAD"), self.git("rev-parse", "main")), (branch, self.first))
        later = "2030-01-06T00:00:00Z"
        self.assertEqual((self.tier(later), self.tier(later, accepted="feature")), (2, 3))
        self.assertEqual(review_ladder.export(self.root)["version"][0]["id"], f"v-{self.first}")
        self.assertEqual(review_ladder.export(self.root, accepted="feature")["version"][0]["id"], f"v-{branch}")

    def test_a_merge_dates_the_table_at_acceptance_and_hides_branch_tables(self):
        """Claim: a table that reaches the accepted branch through a merge
        takes effect at the merge, and the branch's intermediate tables never
        appear in the accepted history. Rejects backdating a table to the
        branch commit that wrote it."""
        self.git("checkout", "--quiet", "-b", "feature")
        edit(self.root, stores.CATALOG, HIGH, 'model = "nw-atlas-2"\neffort = "high"\nrank = 1')
        self.commit("2030-01-04T00:00:00Z")
        edit(self.root, stores.CATALOG, 'model = "nw-atlas-2"\neffort = "high"\nrank = 1', RAISED)
        self.commit("2030-01-05T00:00:00Z")
        self.git("checkout", "--quiet", "main")
        self.git("merge", "--quiet", "--no-ff", "--message", "accept", "feature", date="2030-01-08T00:00:00Z")
        merge = self.git("rev-parse", "HEAD")
        versions = review_ladder.export(self.root, history=True)["version"]
        self.assertEqual([(version["id"], version["effective_from"]) for version in versions[1:]],
                         [(f"v-{self.first}", "2030-01-03T00:00:00Z"), (f"v-{merge}", "2030-01-08T00:00:00Z")])
        self.assertEqual((self.tier("2030-01-06T00:00:00Z"), self.tier("2030-01-09T00:00:00Z")), (2, 3))

    def test_the_witness_reads_the_era_file_as_committed_then(self):
        """Claim: a dated assessment's witness hashes the era file as the
        accepted revision held it, absent included, never the working tree
        or a later commit. Rejects a witness that moves when a later edit
        touches history it does not describe."""
        before = assess_review(self.root, "nw-atlas-2#high", ["ts-3-core#max"],
                               as_of="2030-01-04T00:00:00Z")["route_version"]
        evidence = self.root / review_ladder.EVIDENCE
        evidence.parent.mkdir(parents=True)
        evidence.write_text("the ladder's design record\n")
        self.assertEqual(assess_review(self.root, "nw-atlas-2#high", ["ts-3-core#max"],
                                       as_of="2030-01-04T00:00:00Z")["route_version"], before)
        self.git("add", review_ladder.EVIDENCE)
        self.commit("2030-01-05T00:00:00Z")
        self.assertEqual(assess_review(self.root, "nw-atlas-2#high", ["ts-3-core#max"],
                                       as_of="2030-01-04T00:00:00Z")["route_version"], before)
        self.assertNotEqual(assess_review(self.root, "nw-atlas-2#high", ["ts-3-core#max"],
                                          as_of="2030-01-06T00:00:00Z")["route_version"], before)

    def test_a_revision_whose_seats_name_one_backend_each_is_still_read(self):
        """Claim: an accepted revision whose policy wrote a route as one seat
        row per backend, `backend = "..."`, reads as the same capability table
        and dates assessments like any other. Rejects a ladder that projects
        such a revision as an empty table and refuses every read across it."""
        path = self.root / stores.POLICY
        text = path.read_text().replace('backends = ["codex", "pi"]\nprovider = "tessel-plan"',
                                        'backends = ["codex"]\nprovider = "tessel-plan"')
        survey = text[text.index('[[seat]]\nprofile = "survey"'):text.index("[[seat_rank]]")]
        text = text.replace(survey, survey + survey.replace('backends = ["codex"]', 'backends = ["pi"]'))
        path.write_text(re.sub(r'backends = \["(\w+)"\]', r'backend = "\1"', text))
        self.commit("2030-01-04T00:00:00Z")
        versions = review_ladder.export(self.root, history=True)["version"]
        self.assertEqual([version.get("id") for version in versions[1:]], [f"v-{self.first}"])
        self.assertEqual(self.tier("2030-01-05T00:00:00Z"), 2)

    def test_a_shallow_clone_exports_its_current_table_but_not_history(self):
        """Claim: a shallow clone still exports the current version from the
        commits it holds, and refuses --history it cannot read. Rejects a
        history exported from a truncated record as if complete."""
        clone = scratch(self)
        subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", "main", f"file://{self.root}",
                        str(clone / "repo")], check=True, capture_output=True)
        head = self.git("rev-parse", "HEAD")
        version = review_ladder.export(clone / "repo")["version"][0]
        self.assertEqual(version["id"], f"v-{head}")
        with self.assertRaises(ValueError):
            review_ladder.export(clone / "repo", history=True)


if __name__ == "__main__":
    unittest.main()
