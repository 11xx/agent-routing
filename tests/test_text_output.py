"""Readable views preserve structure while the JSON and store contracts stay fixed."""

import copy
import io
import json
import re
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from edit_fixture import GitStoreTest
import data_edits
import edit_cli
import field_notes
import stores
import text_fixture
import text_output


class TextOutputTest(GitStoreTest):
    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = edit_cli.main(self.root, list(args))
        self.assertEqual(code, 0, err.getvalue() or out.getvalue())
        return out.getvalue()

    def assert_wrapped(self, text, width):
        self.assertTrue(all(len(line) <= width for line in text.splitlines()), "output exceeds the requested width")
        self.assertFalse(any(line.lstrip().startswith(("{", "[")) for line in text.splitlines()), "raw JSON row in text")

    def test_card_structure_and_wrapping(self):
        """Claim: a card leads with aligned seats and scoped guards, orders sections and wraps evidence; rejects JSON rows and mixed evidence sections."""
        data, result = text_fixture.card_result()
        text = data_edits.render(result, width=78, data=data)
        lines = text.splitlines()
        self.assertEqual(lines[0], "nw-atlas-2 · northwind")
        headings = ("Seats", "Prohibited", "Guards", "Weaknesses", "Strengths", "Observations and measurements",
                    "Inherited from nw-atlas-1, unverified for this model")
        for heading in headings:
            self.assertIn(heading, lines, "missing card section")
        positions = [lines.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions), "card sections are out of order")
        seats = [line for line in lines[positions[0] + 1:positions[1]] if re.match(r"  \S+\s+claude\s", line)]
        self.assertGreaterEqual(len(seats), 4)
        self.assertEqual(len({line.index("claude") for line in seats}), 1, "seat columns are not aligned")
        self.assertTrue(any("implement:bounded" in line and "medium" in line for line in seats))
        self.assertIn("experimental ·", text)
        self.assertRegex(text, r"· high, implement: Name exact targets")
        self.assertRegex(text, r"\n\s+why: The fixture")
        self.assertRegex(text, r"\n\s+evidence: ")
        self.assertIn("because n0003", text)
        self.assertRegex(text, r"n0003\s+×2\s+2030-01-06 → 2030-01-09")
        self.assertRegex(text, r"n0005\s+×1\s+2030-01-07\s+A bounded")
        self.assertNotIn("2030-01-07 → 2030-01-07", text)
        self.assert_wrapped(text, 78)
        self.assert_wrapped(data_edits.render(result, width=54, data=data), 54)
        empty = dict(result, seats=[], prohibited=[], guards=[], notes=[], inherited_unverified=[])
        empty_lines = data_edits.render(empty, data=data).splitlines()
        self.assertEqual(sum(line.strip() == "none" for line in empty_lines), 7)
        with patch.object(text_output.sys.stdout, "isatty", return_value=False), patch.dict("os.environ", {"COLUMNS": "140"}):
            self.assertEqual(data_edits.render(result, data=data), data_edits.render(result, data=data, width=80))
        text_fixture.write(self.root)
        before = self.texts()
        expected = dict(schema="agent-routing-card/1", **field_notes.card(stores.Data.from_texts(before), stores.parse_notes(before[stores.NOTES]), "nw-atlas-2"))
        with patch.object(data_edits, "render", side_effect=AssertionError("JSON called the text renderer")):
            self.assertEqual(json.loads(self.cli("card", "nw-atlas-2", "--json")), expected)
        self.assertEqual(self.texts(), before)

    def test_card_lists_the_purposes_a_model_holds_a_review_seat_for(self):
        """Claim: a card names, after its seats, each review purpose the model
        holds a seat for with its author lab, backend, effort and when, and
        says none for a model that holds no review seat. Rejects a card that
        hides which review purposes a model serves."""
        data, result = text_fixture.card_result()
        lines = data_edits.render(result, width=100, data=data).splitlines()
        start, end = lines.index("Review seats"), lines.index("Prohibited")
        self.assertLess(lines.index("Seats"), start)
        self.assertEqual([line.split()[:5] for line in lines[start + 1:end]],
                         [["clearance", "for", "any", "claude", "xhigh"], ["findings", "for", "any", "claude", "xhigh"],
                          ["exhaustive", "for", "any", "claude", "xhigh"]])
        self.assertIn("A whole-surface read from a Northwind session.", lines[end - 1])
        self.assertEqual([row["purpose"] for row in result["review_seats"]], ["clearance", "findings", "exhaustive"])
        swift = dict(schema="agent-routing-card/1", **field_notes.card(data, [], "nw-swift-2"))
        swift_lines = data_edits.render(swift, data=data).splitlines()
        self.assertEqual(swift_lines[swift_lines.index("Review seats") + 1], "  none")

    def test_notes_coordinates_liveness_and_dates(self):
        """Claim: note entries lead with coordinates, recurrence and dates and mark dispositions; rejects raw objects or silently live retired notes."""
        data, records = text_fixture.sample()
        rows = field_notes.select(records, model="nw-atlas-2", liveness="all")
        result = dict(schema="agent-routing-notes/1", notes=rows)
        text = data_edits.render(result, width=96)
        self.assertRegex(text, r"nw-atlas-2 high\s+n0003\s+×2\s+2030-01-06 → 2030-01-09")
        self.assertRegex(text, r"nw-atlas-2 high\s+n0008\s+×1\s+2030-01-08\s+· retracted")
        self.assertRegex(text, r"nw-atlas-2 high\s+n0007\s+×1\s+2030-01-08\s+· superseded")
        self.assertNotIn("2030-01-08 → 2030-01-08", text)
        self.assertIn("reason: The executor was misidentified.", text)
        self.assert_wrapped(text, 96)
        narrow = data_edits.render(result, width=54)
        self.assert_wrapped(narrow, 54)
        self.assertIn("\n    ", narrow)
        self.assertEqual(data_edits.render(dict(schema="agent-routing-notes/1", notes=[])), "none")
        text_fixture.write(self.root)
        with patch.object(data_edits, "render", side_effect=AssertionError("JSON called the text renderer")):
            self.assertEqual(json.loads(self.cli("notes", "nw-atlas-2", "--liveness", "all", "--json"))["notes"], rows)

    def test_edit_changed_fields_addition_and_removal(self):
        """Claim: edit text names its row and only changed fields, with wrapped sentences; rejects full before/after JSON and hidden removals."""
        result = self.seat(dry_run=True)
        original = copy.deepcopy(result)
        text = data_edits.render(result, width=72)
        self.assertIn("dry run", text.splitlines()[0])
        self.assertIn("data/policy.toml seat implement:flat (backends: pi)", text)
        change = result["changes"][0]
        expected = {key for key in change["after"] if change["before"].get(key) != change["after"][key]}
        actual = {match[1] for line in text.splitlines() if (match := re.match(r"  (\w+): ", line))}
        self.assertEqual(actual, expected, "unchanged fields were printed or changed fields were omitted")
        self.assertIn("effort: max → low", text)
        self.assertNotIn("before:", text)
        self.assertNotIn("after:", text)
        self.assert_wrapped(text, 72)
        for key in expected:
            self.assertEqual(len(re.findall(rf"^  {key}: ", text, re.M)), 1)
        addition = dict(result, changes=[dict(change, before=None)])
        added = data_edits.render(addition, width=72)
        self.assertIn("added", added)
        self.assertIn("  model: orbit-flash", added)
        removal = dict(result, changes=[dict(change, after=None)])
        removed = data_edits.render(removal, width=72)
        self.assertIn("removed", removed)
        self.assertNotIn("  effort:", removed)
        long = copy.deepcopy(result)
        long["changes"][0]["after"]["why"] = "A long explanation gives readers the reason for changing this one field while preserving the other row values."
        self.assert_wrapped(data_edits.render(long, width=54), 54)
        self.assertEqual(result, original, "text formatting changed the JSON result")
        with patch.object(data_edits, "apply", return_value=result), patch.object(data_edits, "render", side_effect=AssertionError("JSON called the text renderer")):
            self.assertEqual(json.loads(self.cli("set-seat", "implement", "--variant", "flat", "--backend", "pi", "--model", "orbit-flash", "--effort", "low", "--when", "Bounded work.", "--why", "Use this tier.", "--json")), result)

    def test_log_one_line_date_verb_row_and_reason(self):
        """Claim: log shows one dated edit per line with verb, row and first reason sentence; rejects subject-only or multiline history."""
        result = self.apply("rank", model="ts-3-core", effort="low", rank=1, floor=2,
                            why="Use the measured tier. Keep the second sentence private to the full history.")
        before = data_edits.history(self.root, limit=1)
        text = self.cli("log", "--limit", "1")
        self.assertEqual(len(text.splitlines()), 1)
        self.assertRegex(text, rf"^{result['commit'][:12]}\s+\d{{4}}-\d{{2}}-\d{{2}}\s+rank\s+")
        self.assertIn("tier ts-3-core low", text)
        self.assertIn("Use the measured tier.", text)
        self.assertNotIn("Keep the second sentence", text)
        self.assertNotIn("Routing-edit:", text)
        with patch.object(data_edits, "render", side_effect=AssertionError("JSON called the text renderer")):
            self.assertEqual(json.loads(self.cli("log", "--limit", "1", "--json")), dict(schema="agent-routing-history/1", edits=before))
        self.assertEqual(data_edits.history(self.root, limit=1), before)
