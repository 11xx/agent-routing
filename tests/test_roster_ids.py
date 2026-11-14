"""The invariant that keeps catalog ids out of code and tests, over the fixture tree."""

import subprocess
import unittest

from fixture import scratch


class RosterIdsTest(unittest.TestCase):
    def test_a_catalog_id_in_a_test_is_refused_by_line(self):
        """Claim: a catalog model id, alias or backend model string anywhere
        under lib/, bin/, templates/ or tests/ fails the lint, naming the file,
        line and model; a near miss passes. Rejects a test or module that
        names the roster it should read."""
        root = scratch(self, code=True)
        lint = [str(root / "bin" / "lint-roster-ids")]
        (root / "tests").mkdir()
        (root / "tests" / "test_planted.py").write_text("NEAR = 'orbit-flashy'\n")
        self.assertEqual(subprocess.run(lint, capture_output=True).returncode, 0)
        (root / "tests" / "test_planted.py").write_text("NEAR = 'orbit-flashy'\nPINNED = 'claude-atlas-2#high'\n")
        result = subprocess.run(lint, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("tests/test_planted.py:2: catalog id 'claude-atlas-2' (model nw-atlas-2)", result.stdout)


if __name__ == "__main__":
    unittest.main()
