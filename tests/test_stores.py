"""The stores' emitter, parser and validator over the fixture data."""

import hashlib
import json
import unittest

from fixture import FIXTURE, ROOT, edit, scratch

import routing_profiles
import stores


class EmitterTest(unittest.TestCase):
    def test_each_store_round_trips_byte_for_byte(self):
        """Claim: emitting a parsed store reproduces its bytes exactly.
        Rejects an emitter that reorders, reformats or drops anything."""
        for name, emit in ((stores.CATALOG, stores.emit_catalog), (stores.POLICY, stores.emit_policy)):
            text = (FIXTURE / name).read_text()
            self.assertEqual(emit(stores.parse_toml(text, name)), text, name)
        notes = (FIXTURE / stores.NOTES).read_text()
        self.assertEqual(stores.emit_notes(stores.parse_notes(notes)), notes)

    def test_key_and_table_order_do_not_change_the_output(self):
        """Claim: the emitter fixes key order and writes each member row after
        its owner, keeping the rows' relative order, whatever order keys and
        tables arrive in. Rejects output that depends on how a caller built
        the document."""
        text = (FIXTURE / stores.CATALOG).read_text()
        document = stores.parse_toml(text, stores.CATALOG)
        scrambled = {table: [dict(reversed(list(row.items()))) for row in value] if isinstance(value, list)
                     else value for table, value in reversed(list(document.items()))}
        self.assertEqual(stores.emit_catalog(scrambled), text)

    def test_an_unknown_key_is_refused_naming_the_row(self):
        """Claim: a key the schema does not declare is refused with the row's
        identity. Rejects silently carrying, or silently dropping, a stray field."""
        root = scratch(self)
        edit(root, stores.POLICY, 'id = "plan"\npurpose', 'id = "plan"\ncolour = "red"\npurpose')
        problems = stores.shape_problems(stores.parse_toml((root / stores.POLICY).read_text(), stores.POLICY),
                                         stores.POLICY_TABLES, stores.POLICY, stores.POLICY_SETTINGS)
        self.assertIn("data/policy.toml [[profile]] id=plan: unknown key 'colour'", problems)

    def test_route_version_hashes_catalog_and_policy_but_not_notes(self):
        """Claim: route_version is the first twelve hex digits of SHA-256 over
        each of catalog and policy as path, NUL, bytes, NUL, and a note never
        moves it. Rejects a version that misses a store or reacts to notes."""
        digest = hashlib.sha256()
        for name in (stores.CATALOG, stores.POLICY):
            digest.update(name.encode() + b"\0" + (FIXTURE / name).read_bytes() + b"\0")
        self.assertEqual(routing_profiles.route_version(ROOT), digest.hexdigest()[:12])
        root = scratch(self)
        before = routing_profiles.route_version(root)
        with (root / stores.NOTES).open("a") as notes:
            notes.write(stores.emit_note({"id": "n0003", "date": "2030-01-06", "model": "orbit-flash",
                                          "kind": "observation", "areas": ["latency"], "claim": "Fast.",
                                          "cause": "unknown", "evidence": "fixture"}))
        self.assertEqual(routing_profiles.route_version(root), before)
        edit(root, stores.POLICY, "clearance = 2", "clearance = 3")
        self.assertNotEqual(routing_profiles.route_version(root), before)


class ValidatorTest(unittest.TestCase):
    def test_the_fixture_is_valid(self):
        """Claim: the fixture data set passes the whole-data validator.
        Rejects a fixture the rest of the suite would read as broken."""
        self.assertEqual(routing_profiles.data_problems(FIXTURE), [])

    def test_each_problem_names_its_row(self):
        """Claim: the validator names the store and the offending row for a
        mistyped field, a paragraph in a seat, and a malformed note. Rejects
        a validator that reports only that something is wrong."""
        root = scratch(self)
        edit(root, stores.CATALOG, 'model = "ts-3-core"\neffort = "high"\nrank = 1',
             'model = "ts-3-core"\neffort = "high"\nrank = "one"')
        edit(root, stores.POLICY, 'when = "Specified implementation from pi."',
             'when = "Specified implementation from pi. It also explains itself."')
        with (root / stores.NOTES).open("a") as notes:
            notes.write('{"id": "n0001", "date": "2030-01-06", "model": "nobody", "kind": "rumour", "areas": [], '
                        '"claim": "x", "cause": "unknown", "evidence": "x"}\n')
        problems = routing_profiles.data_problems(root)
        for expected in (
                "data/catalog.toml [[tier]] model=ts-3-core effort=high: rank must be an integer, not 'one'",
                "data/policy.toml [[seat]] profile=implement variant=flat backend=pi: when is one sentence "
                "of at most 240 characters",
                "data/notes.jsonl note 'n0001': id is used twice",
                "data/notes.jsonl note 'n0001': model 'nobody' is not a catalog model",
                "data/notes.jsonl note 'n0001': kind must be one of strength, weakness, observation, measurement"):
            self.assertIn(expected, problems)

    def test_a_seat_on_an_unreachable_model_is_refused(self):
        """Claim: a seat whose model has no reach row for its backend and
        provider is refused. Rejects a route that names a model the backend
        cannot launch."""
        root = scratch(self)
        edit(root, stores.CATALOG, '[[reach]]\nmodel = "orbit-flash"\nbackend = "pi"\nprovider = "flat-pool"\n'
             'backend_model = "orbit-flash-0101"\n\n', "")
        problems = routing_profiles.data_problems(root)
        self.assertTrue(any("seat" in problem and "orbit-flash" in problem for problem in problems), problems)

    def test_no_decision_reads_the_notes(self):
        """Claim: corrupting the notes changes no resolver answer. Rejects a
        verb that selects, validates or refuses a route from field notes."""
        root = scratch(self)
        before = routing_profiles.resolve(root, "implement", "codex")
        (root / stores.NOTES).write_text("not json\n")
        self.assertEqual(routing_profiles.resolve(root, "implement", "codex"), before)


class FormatVerbTest(unittest.TestCase):
    def test_format_check_names_a_hand_edit_and_format_rewrites_it(self):
        """Claim: the canonical check names a store that is not canonical, and
        formatting rewrites it to the canonical bytes. Rejects a check that
        passes non-canonical bytes or a rewrite that changes content."""
        root = scratch(self)
        edit(root, stores.CATALOG, 'id = "orbit-trial"\nfamily = "orbit"', 'family = "orbit"\nid = "orbit-trial"')
        self.assertEqual(stores.canonical_problems(root),
                         [f"{stores.CATALOG}: not in canonical form; `agent-routing format` rewrites it"])
        self.assertEqual(stores.format_stores(root), [stores.CATALOG])
        self.assertEqual((root / stores.CATALOG).read_text(), (FIXTURE / stores.CATALOG).read_text())
        self.assertEqual(stores.canonical_problems(root), [])

    def test_note_lines_keep_a_fixed_key_order(self):
        """Claim: a note's keys are written id, date, model, effort, kind, areas,
        claim, cause, evidence, metrics, with metrics sorted. Rejects notes whose
        layout depends on the writer."""
        line = stores.emit_note({"metrics": {"b": 1, "a": "x"}, "evidence": "e", "cause": "unknown",
                                 "claim": "c.", "areas": ["t"], "kind": "measurement", "model": "m",
                                 "date": "2030-01-01", "id": "n0001"})
        self.assertEqual(list(json.loads(line)), ["id", "date", "model", "kind", "areas", "claim", "cause",
                                                  "evidence", "metrics"])
        self.assertIn('"metrics": {"a": "x", "b": 1}', line)


if __name__ == "__main__":
    unittest.main()
