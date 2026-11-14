"""The public edit flags reach library operations without changing their result contract."""

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from edit_fixture import GitStoreTest
from fixture import build, run_command
import data_edits
import edit_cli
import stores


class EditCliTest(GitStoreTest):
    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = edit_cli.main(self.root, [*args, "--json"])
        self.assertEqual(code, 0, err.getvalue() or out.getvalue())
        return json.loads(out.getvalue())

    def test_note_correction_keeps_omitted_fields(self):
        """Claim: a CLI correction inherits omitted fields and publishes one JSON object; rejects replacing them with nulls."""
        self.cli("supersede", "n0001", "--claim", "Passed a corrected fixture probe.", "--evidence", "fixture:corrected",
                 "--reason", "Correct the recorded outcome.")
        live = self.cli("notes", "ts-3-core", "--kind", "strength", "--area", "implementation")["notes"]
        self.assertEqual(len(live), 1)
        self.assertEqual((live[0]["model"], live[0]["effort"], live[0]["cause"]), ("ts-3-core", "max", "executor"))
        self.assertEqual(len(self.cli("log", "--limit", "1")["edits"]), 1)
        card = self.cli("card", "ts-3-core")
        self.assertEqual(card["notes"][0]["id"], live[0]["id"])

    def test_wrapper_and_json_refusal(self):
        """Claim: the executable wrapper uses its fixture root and returns structured refusal; rejects reading the live tree."""
        build(self.root, code=True)
        args = ["remove-seat", "implement", "--variant", "flat", "--why", "Reject removal of a default.", "--json", "--dry-run"]
        code, out, err = run_command(self.root / "bin" / "edit-data", args)
        self.assertEqual(code, 1, err)
        result = json.loads(out)
        self.assertEqual(result["schema"], "agent-routing-edit-error/1")
        self.assertIn("profile=implement", result["error"])
        self.assertIn("resolvable default", result["error"])

    def test_attribution_comes_only_from_arc_env(self):
        """Claim: acting coordinates come from arc env and absent coordinates stay absent; rejects guessing from ambient defaults."""
        import subprocess
        self.identity_patch.stop()
        with patch.object(data_edits.subprocess, "run", return_value=subprocess.CompletedProcess([], 0,
                "export ARC_HARNESS='fixture' ARC_SESSION='irrelevant'\n# model: invented#high\n", "")):
            self.assertEqual(data_edits.attribution(self.root), "fixture:invented#high")
        with patch.object(data_edits.subprocess, "run", return_value=subprocess.CompletedProcess([], 0,
                "export ARC_HARNESS='fixture'\n", "")):
            self.assertIsNone(data_edits.attribution(self.root))
