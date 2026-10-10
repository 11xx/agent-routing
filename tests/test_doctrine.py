"""The doctrine documents: the manifest agreement gate and the guide fences.

`bin/lint-routing` locates both documents from its own path, so a fixture is a
copy of the tree it reads: perturb the copy, run the script there, and the
failure is the real one a drifting edit would produce. The guide tests read the
authored document directly, because that is what the bare CLI prints.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class DoctrineLintTest(unittest.TestCase):
    def fixture_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        for directory in ("bin", "lib", "routing", "doctrine"):
            shutil.copytree(ROOT / directory, root / directory)
        return root

    def run_lint(self, root):
        return subprocess.run(
            [sys.executable, root / "bin" / "lint-routing"],
            capture_output=True,
            text=True,
        )

    def rewrite_doctrine(self, root, old, new):
        path = root / "doctrine" / "model-routing.md"
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def test_authored_documents_agree(self):
        self.assertEqual(self.run_lint(self.fixture_root()).returncode, 0)

    def test_drifting_measured_cell_is_reported(self):
        root = self.fixture_root()
        self.rewrite_doctrine(
            root, "| opus-5 · high | 73% | 6.08", "| opus-5 · high | 73% | 6.09"
        )
        result = self.run_lint(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("opus-5 high: doctrine $ cell", result.stdout)

    def test_dropping_a_predecessor_figure_is_reported(self):
        root = self.fixture_root()
        self.rewrite_doctrine(
            root,
            "— (V4 Flash 0731: 53% / $0.46)",
            "— (V4 Flash 0731, unmeasured here)",
        )
        result = self.run_lint(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("predecessor pass@1 53", result.stdout)
        self.assertIn("predecessor $ 0.46", result.stdout)


class GuideFenceTest(unittest.TestCase):
    """The bare `agent-routing` guide carries the review and delegation fences.

    The guide is where the reasoning behind a fence is read, so these tests
    read the authored document rather than a lint's copy of it.
    """

    def normalized_guide(self):
        return " ".join((ROOT / "doctrine" / "guide.md").read_text().split())

    def test_self_review_is_not_independent_review(self):
        guide = self.normalized_guide()
        self.assertIn("authored the patchset is not independent", guide)
        self.assertIn(
            "a lead that did not write the implementation reviews it", guide
        )

    def test_debt_never_overrides_a_changes_requested_verdict(self):
        guide = self.normalized_guide()
        self.assertIn("Debt is a routine record of deferred coverage", guide)
        self.assertIn(
            "never overrides an actual changes-requested verdict", guide
        )


class RoutingInstructionTest(unittest.TestCase):
    def instruction(self, title):
        return next(line for line in (ROOT / "doctrine" / "model-routing.md").read_text().splitlines()
                    if line.startswith(f"- **{title}"))

    def computer_use_profile(self):
        profiles = tomllib.loads((ROOT / "routing" / "profiles.toml").read_text())["profile"]
        return next(profile for profile in profiles if profile["id"] == "computer-use")

    def sol_display_model(self):
        return self.computer_use_profile()["model"].replace("gpt-", "GPT-").replace("-sol", " Sol")

    def test_computer_use_instruction_names_the_profile_successor(self):
        instruction = self.instruction("Delegated workhorse")
        expected = f'profile starts at **{self.sol_display_model()} {self.computer_use_profile()["effort"]}**'
        self.assertIn(expected, instruction)
        self.assertNotIn("GPT-6 Sol", instruction)

    def test_quota_handoff_names_the_sol_successor(self):
        instruction = self.instruction("Quota is bidirectional")
        self.assertIn(f"codex ({self.sol_display_model()})", instruction)
        self.assertNotIn("GPT-6 Sol", instruction)

    def execute_profile(self):
        profiles = tomllib.loads((ROOT / "routing" / "profiles.toml").read_text())["profile"]
        return next(profile for profile in profiles if profile["id"] == "execute")

    def test_judgment_instruction_uses_the_execute_effort(self):
        instruction = self.instruction("Delegation effort is priced")
        self.assertIn(f'Escalate to {self.sol_display_model()} **{self.execute_profile()["effort"]}**', instruction)

    def test_migration_and_declined_escalation_instructions_keep_the_floor(self):
        floor = f'Sol-{self.execute_profile()["effort"]} floor'
        for title in ("Delegation effort is priced", "An escalation above the caller's own seat"):
            with self.subTest(title=title):
                instruction = self.instruction(title)
                self.assertIn(floor, instruction)
                self.assertNotIn("Sol-high floor", instruction)

    def test_delegation_rationale_names_the_judgment_effort(self):
        rules = tomllib.loads((ROOT / "routing" / "delegation.toml").read_text())["rule"]
        rationale = next(rule["why"] for rule in rules if rule["id"] == "native-subagent-fence")
        self.assertIn(f'lead judgment to Sol {self.execute_profile()["effort"]}', rationale)
