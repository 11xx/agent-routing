"""The capability ladder read from Git history, over a scratch repository of the fixture data."""

import os
import subprocess
import unittest
from unittest import mock

from fixture import edit, scratch

import review_ladder
import stores

IDENTITY = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@localhost",
            "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@localhost"}


class LadderTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
