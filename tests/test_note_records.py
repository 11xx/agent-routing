"""The append-only note record format and its current-state projection."""

import copy
import unittest

from fixture import FIXTURE
import field_notes
import stores


class NoteRecordsTest(unittest.TestCase):
    def test_lifecycle(self):
        """Claim: append-only events derive liveness and recurrence; rejects changing the original note record."""
        records = stores.load_notes(FIXTURE)
        original = copy.deepcopy(records)
        records += [dict(id="n0003", date="2030-01-06", event="again", note="n0001", evidence="fixture:repeat"),
                    dict(id="n0004", date="2030-01-07", event="retract", note="n0002", reason="Misread score.")]
        self.assertEqual(stores.note_problems(records, stores.load(FIXTURE).catalog), [])
        self.assertEqual(records[:2], original)
        live = field_notes.select(records)
        self.assertEqual([(row["id"], row["occurrences"]) for row in live], [("n0001", 2)])
        self.assertEqual(stores.parse_notes(stores.emit_notes(records)), records)
        self.assertEqual(field_notes.next_id([dict(id="n9999")]), "n10000")
        self.assertEqual(field_notes.next_id([dict(id="n10000")]), "n10001")
