"""Field evidence stays append-only and has no routing authority."""

import copy

from edit_fixture import GitStoreTest
import field_notes
import stores


class NoteTest(GitStoreTest):
    def test_ids_append_one_line(self):
        """Claim: consecutive notes allocate consecutive ids and append one line; rejects overwrite or reuse."""
        before = self.texts()[stores.NOTES]
        first = self.note()
        second = self.note(evidence="fixture:two")
        after = self.texts()[stores.NOTES]
        self.assertEqual((first["record_id"], second["record_id"]), ("n0003", "n0004"))
        self.assertTrue(after.startswith(before))
        self.assertEqual(len(after.splitlines()) - len(before.splitlines()), 2)
        self.assertEqual(first["old_route_version"], second["new_route_version"])

    def test_again_changes_card_order(self):
        """Claim: recurrence outranks recency and retains dated evidence; rejects treating a recurrence as a new note."""
        newer = self.note()
        records = stores.load_notes(self.root)
        self.assertEqual(field_notes.card(stores.load(self.root), records, "ts-3-core")["notes"][0]["id"], newer["record_id"])
        self.apply("again", note="n0001", evidence="fixture:again", date="2030-02-02")
        card = field_notes.card(stores.load(self.root), stores.load_notes(self.root), "ts-3-core")
        row = card["notes"][0]
        self.assertEqual((row["id"], row["occurrences"], row["last_seen"]), ("n0001", 2, "2030-02-02"))
        self.assertIn({"date": "2030-02-02", "reference": "fixture:again"}, row["evidence"])

    def test_events(self):
        """Claim: retract and supersede append dispositions and exclude old notes; rejects editing earlier evidence."""
        before = self.texts()[stores.NOTES]
        self.apply("retract", note="n0001", reason="The evidence named the wrong executor.")
        middle = self.texts()[stores.NOTES]
        self.apply("supersede", note="n0002", claim="The corrected board scores it at a quarter.",
                   evidence="fixture:corrected", reason="The earlier score was misread.")
        after = self.texts()[stores.NOTES]
        self.assertTrue(middle.startswith(before))
        self.assertTrue(after.startswith(middle))
        records = stores.load_notes(self.root)
        live = field_notes.select(records)
        self.assertEqual([row["id"] for row in live], ["n0004"])
        self.assertEqual(live[0]["claim"], "The corrected board scores it at a quarter.")
        self.assertEqual([row["id"] for row in field_notes.select(records, liveness="inactive")], ["n0002", "n0001"])
        self.assertEqual(stores.note_problems(records, stores.load(self.root).catalog), [])

    def test_growth_rejects_earlier_changes(self):
        """Claim: append-only validation rejects an earlier byte edit; rejects checking line count alone."""
        before = self.texts()[stores.NOTES].encode()
        self.assertEqual(field_notes.grows_only(before, before + b'{}\n'), [])
        self.assertIn("append-only", field_notes.grows_only(before, before.replace(b"fixture", b"changed", 1))[0])

    def test_card_marks_inheritance(self):
        """Claim: a successor sees predecessor notes as inherited and unverified; rejects presenting them as direct evidence."""
        self.apply("add-model", model="ts-next", family="ts-3", tier=[dict(effort="high", rank=2, floor=2)],
                   reach=[dict(backend="codex", provider="tessel-plan", backend_model="ts-next")], why="Register the successor.")
        texts = self.texts()
        catalog = stores.parse_toml(texts[stores.CATALOG], stores.CATALOG)
        next(row for row in catalog["model"] if row["id"] == "ts-3-core")["successor"] = "ts-next"
        data = stores.Data(catalog, stores.parse_toml(texts[stores.POLICY], stores.POLICY), "fixture")
        card = field_notes.card(data, stores.load_notes(self.root), "ts-next")
        self.assertEqual(card["notes"], [])
        self.assertEqual([row["id"] for row in card["inherited_unverified"]], ["n0001"])

    def test_filters_and_event_validation(self):
        """Claim: filters compose and malformed event references are named; rejects silently accepting dangling events."""
        self.note()
        rows = stores.load_notes(self.root)
        self.assertEqual(len(field_notes.select(rows, model="ts-3-core", kind="strength", area="implementation")), 2)
        self.assertEqual(field_notes.select(rows, area="unknown"), [])
        for event in (dict(id="n0004", date="2030-02-02", event="again", note="n9999", evidence="fixture"),
                      dict(id="n0004", date="2030-02-02", event="supersede", note="n0001", reason="Wrong.", replacement="n9999")):
            self.assertTrue(stores.note_problems([*copy.deepcopy(rows), event], stores.load(self.root).catalog))

    def test_undo_note_appends_compensation(self):
        """Claim: undo of evidence appends compensation and restores liveness; rejects deleting the original line."""
        self.apply("retract", note="n0001", reason="A mistaken retraction.")
        before = self.texts()[stores.NOTES]
        self.apply("undo", why="Restore the verified observation.")
        self.assertTrue(self.texts()[stores.NOTES].startswith(before))
        self.assertIn("n0001", [row["id"] for row in field_notes.select(stores.load_notes(self.root))])

    def test_history_catches_a_rewrite_hidden_by_restoration(self):
        """Claim: every intervening revision grows notes; rejects a net-only comparison that hides a rewritten line."""
        import data_edits
        path = self.root / stores.NOTES
        before = path.read_bytes()
        path.write_bytes(before.replace(b"fixture", b"changed", 1))
        self.git("add", stores.NOTES)
        self.git("commit", "--quiet", "-m", "Rewrite earlier evidence")
        path.write_bytes(before)
        self.git("add", stores.NOTES)
        self.git("commit", "--quiet", "-m", "Restore earlier evidence")
        self.assertTrue(data_edits.notes_history_problems(self.root, self.base))
