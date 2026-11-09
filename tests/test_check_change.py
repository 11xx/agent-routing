"""bin/check-change holds a change to its declarations and to the base's invariants.

Each test copies this repository's code into a scratch Git repository whose
base commit lists one invariant, adds the change's commits, and runs the gate
there against that base.
"""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
COPIED = ("bin", "lib", "templates", "tests")
IDENTITY = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@localhost",
            "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@localhost"}
GUARD = '[[invariant]]\nname = "guard"\ncommand = "test ! -e broken"\n'


class CheckChangeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.cache = pathlib.Path(temporary.name) / "cache"
        self.repo = pathlib.Path(temporary.name) / "repo"
        listed = subprocess.run(["git", "-C", str(REPOSITORY), "ls-files", "--cached", "--others",
                                 "--exclude-standard", "--", *COPIED], capture_output=True, text=True, check=True)
        for name in listed.stdout.splitlines():
            source = REPOSITORY / name
            if source.is_file():
                (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, self.repo / name)
        self.git("init", "--quiet", "--initial-branch=master")
        self.base = self.commit("chore: establish the base", {"checks/invariants.toml": GUARD})

    def git(self, *args, stdin=None):
        result = subprocess.run(["git", "-C", str(self.repo), "-c", "commit.gpgsign=false", *args],
                                input=stdin, capture_output=True, text=True, env={**os.environ, **IDENTITY})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit(self, message, files):
        for name, content in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.git("add", "--all")
        self.git("commit", "--quiet", "--file=-", stdin=message)
        return self.git("rev-parse", "HEAD")

    def check(self):
        return subprocess.run([self.repo / "bin" / "check-change", "--base", self.base], capture_output=True,
                              text=True, env={**os.environ, "XDG_CACHE_HOME": str(self.cache)})

    def receipt(self):
        """The newest run's receipt."""
        newest = max((self.cache / "agent-routing" / "checks").glob("*.json"))
        return json.loads(newest.read_text())

    def test_a_code_commit_without_a_witness_fails_naming_it(self):
        """Claim: a commit touching lib/ with no Witness trailer fails the gate,
        which names that commit, while a Markdown-only commit needs none.
        Rejects a gate that lets code land with nothing to witness it."""
        self.commit("docs: note the fixture\n", {"NOTES.md": "A prose change.\n"})
        self.assertEqual(self.check().returncode, 0)
        source = self.repo / "lib" / "quota_routing.py"
        commit = self.commit("feat: touch the quota code\n", {"lib/quota_routing.py": source.read_text() + "\n"})
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(f"{commit[:12]} 'feat: touch the quota code' touches lib/quota_routing.py", result.stderr)
        self.assertEqual(self.receipt()["failure"]["phase"], "declarations")

    def test_a_fourth_witness_is_refused(self):
        """Claim: a change naming four distinct witnesses is refused before any
        of them runs. Rejects a gate whose witness phase grows with the change."""
        names = ("test_seats.py::SeatViewTest.test_one", "test_seats.py::SeatViewTest.test_two",
                 "test_quota.py::QuotaAdmissionTest.test_three", "test_quota.py::QuotaAdmissionTest.test_four")
        trailers = "".join(f"Witness: tests/{name}\n" for name in names)
        self.commit(f"test: name four witnesses\n\n{trailers}", {"tests/test_seats.py": "\n"})
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(f"'tests/{names[3]}' is refused", result.stderr)
        self.assertNotIn("witnesses", self.receipt()["phases"])

    def test_an_invariant_the_candidate_drops_still_runs_from_the_base(self):
        """Claim: an invariant the base lists runs even when the candidate's
        list drops it, and fails what it guards. Rejects a change that removes
        the check covering what it breaks."""
        self.commit("chore: drop the guard\n\nWitness: none (the invariant list is the change)\n",
                    {"checks/invariants.toml": "", "broken": "\n"})
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("invariants: invariant guard failed", result.stderr)

    def test_a_skipped_witness_fails(self):
        """Claim: a named witness that skips fails the gate. Rejects counting a
        test that did not run as coverage."""
        test = ("import unittest\n\n\nclass Skipped(unittest.TestCase):\n"
                "    @unittest.skip('not run')\n    def test_skipped(self):\n        pass\n")
        self.commit("test: add a skipped test\n\nWitness: tests/test_skipped.py::Skipped.test_skipped\n",
                    {"tests/test_skipped.py": test})
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("witness tests/test_skipped.py::Skipped.test_skipped did not pass", result.stderr)
        self.assertIn('"skipped": 1', result.stderr)


if __name__ == "__main__":
    unittest.main()
