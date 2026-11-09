"""The doctrine agreement gate reports a doctrine cell that drifts from the manifest.

`bin/lint-routing` locates both documents from its own path, so a fixture is a
copy of the tree it reads: perturb the copy, run the script there, and the
failure is the real one a drifting edit would produce.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from roster import ROOT  # noqa: E402


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
