"""The stores' emitter, parser and validator over the fixture data."""

import copy
import hashlib
import json
import re
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

    def test_every_character_toml_escapes_round_trips(self):
        """Claim: a string holding the quote, the backslash, any control
        character or DEL is written as a valid TOML basic string and parses
        back to itself. Rejects writing DEL raw, which tomllib refuses, so a
        formatted hand edit became unreadable."""
        characters = ['"', "\\", *map(chr, range(0x20)), "\x7f"]
        document = stores.parse_toml((FIXTURE / stores.CATALOG).read_text(), stores.CATALOG)
        for character in characters:
            with self.subTest(character=hex(ord(character))):
                document["tier"][0]["reason"] = f"before{character}after"
                text = stores.emit_catalog(document)
                self.assertEqual(stores.parse_toml(text, stores.CATALOG)["tier"][0]["reason"],
                                 f"before{character}after")
                self.assertEqual(stores.emit_catalog(stores.parse_toml(text, stores.CATALOG)), text)


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
        self.assertIn("data/catalog.toml [[tier]] model=ts-3-core effort=high: rank must be an integer, not 'one'",
                      routing_profiles.data_problems(root))
        root = scratch(self)
        edit(root, stores.POLICY, 'when = "Specified implementation from pi."',
             'when = "Specified implementation from pi. It also explains itself."')
        with (root / stores.NOTES).open("a") as notes:
            notes.write('{"id": "n0001", "date": "2030-01-06", "model": "nobody", "kind": "rumour", "areas": [], '
                        '"claim": "x", "cause": "unknown", "evidence": "x"}\n')
        problems = routing_profiles.data_problems(root)
        for expected in (
                "data/policy.toml [[seat]] profile=implement variant=flat: when is one sentence of at most 240 "
                "characters",
                "data/notes.jsonl note 'n0001': id is used twice",
                "data/notes.jsonl note 'n0001': model 'nobody' is not a catalog model",
                "data/notes.jsonl note 'n0001': kind must be one of strength, weakness, observation, measurement"):
            self.assertIn(expected, problems)

    def test_every_malformed_shape_is_a_diagnostic_never_an_exception(self):
        """Claim: for every table and key of both stores, a wrong scalar type,
        a table where an array of tables belongs, a missing required key and
        an unknown key each yield a problem naming the store and table, and
        nothing is projected from the malformed data. Rejects projecting raw
        rows before their shape is known, which raised TypeError,
        AttributeError and KeyError instead of naming the row."""
        documents = {stores.CATALOG: (stores.CATALOG_TABLES, {}),
                     stores.POLICY: (stores.POLICY_TABLES, stores.POLICY_SETTINGS)}
        pristine = {name: stores.parse_toml((FIXTURE / name).read_text(), name) for name in documents}
        checked = 0
        for store, (tables, settings) in documents.items():
            for table, spec in [*tables.items(), *settings.items()]:
                setting = table in settings
                self.assertIn(table, pristine[store], f"the fixture has no {table} rows to mutate")
                cases = [("container", None, ("must be a table" if setting else "must be an array of tables")),
                         ("unknown", "colour", "unknown key 'colour'")]
                for key, _, required in spec:
                    cases.append(("type", key, f"{key} must be"))
                    if required:
                        cases.append(("missing", key, f"{key} is required"))
                for mutation, key, expected in cases:
                    docs = copy.deepcopy(pristine)
                    rows = docs[store][table]
                    row = rows if setting else rows[0]
                    if mutation == "container":
                        docs[store][table] = [rows] if setting else rows[0]
                    elif mutation == "unknown":
                        row["colour"] = "red"
                    elif mutation == "type":
                        row[key] = {"nested": 1}
                    else:
                        row.pop(key, None)
                    with self.subTest(store=store, table=table, mutation=mutation, key=key):
                        data = stores.Data(docs[stores.CATALOG], docs[stores.POLICY], "fixture")
                        prefix = f"{store}: [{table}]" if setting and mutation == "container" else (
                            f"{store} [{table}]" if setting else f"{store}: [[{table}]]" if mutation == "container"
                            else f"{store} [[{table}]]")
                        self.assertTrue(any(problem.startswith(prefix) and expected in problem
                                            for problem in data.problems), data.problems)
                        self.assertEqual((data.models, data.profiles), ([], []))
                        checked += 1
        self.assertGreater(checked, 150)

    def test_the_reviewers_malformed_inputs_are_refused_by_row(self):
        """Claim: aliases written as a number, a [tier] table in place of
        [[tier]] rows, and a reach row without its backend_model are each
        named by lint and refused by resolve as manifest-invalid. Rejects the
        TypeError, AttributeError and KeyError those inputs raised."""
        cases = [(stores.CATALOG, 'aliases = ["northwind-atlas-2"]', "aliases = 3",
                  "data/catalog.toml [[model]] id=nw-atlas-2: aliases must be a list of distinct nonblank strings, "
                  "not 3"),
                 (stores.CATALOG, None, None, "data/catalog.toml: [[tier]] must be an array of tables"),
                 (stores.CATALOG, 'provider = "flat-pool"\nbackend_model = "orbit-flash-0101"\n',
                  'provider = "flat-pool"\n',
                  "data/catalog.toml [[reach]] model=orbit-flash backend=pi provider=flat-pool: backend_model is "
                  "required")]
        for store, old, new, expected in cases:
            with self.subTest(expected=expected):
                root = scratch(self)
                if old is None:
                    text = re.sub(r"\[\[tier\]\]\n(?:[^\n]+\n)+\n?", "", (root / store).read_text())
                    (root / store).write_text(text + '\n[tier]\nmodel = "orbit-trial"\neffort = "high"\n'
                                              'rank = 1\nfloor = 1\n')
                else:
                    edit(root, store, old, new)
                self.assertIn(expected, routing_profiles.data_problems(root))
                with self.assertRaises(routing_profiles.RouteRefusal) as caught:
                    routing_profiles.resolve(root, "implement", "codex")
                self.assertEqual(caught.exception.kind, "manifest-invalid")
                self.assertIn(expected, str(caught.exception))

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
