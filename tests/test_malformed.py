"""Every command over malformed data: a diagnostic naming the row, never a traceback; and guards and
notes, which no deciding verb reads, never take routing down."""

import json
import re
import unittest

from fixture import edit, run_command, scratch

import review_ladder
import stores

DIAGNOSTIC = "data/catalog.toml [[model]] id=nw-atlas-2: aliases must be a list of distinct nonblank strings, not 3"
COMMANDS = {
    "lint-routing": [],
    "routing-check": ["nw-atlas-2", "max"],
    "resolve-route": ["implement", "--backend", "codex", "--json"],
    "validate-selection": ["--profile", "implement", "--backend", "codex", "--model", "ts-3-core", "--effort", "max",
                           "--provider", "tessel-plan", "--reason", "fixture", "--json"],
    "assess-review": ["--reviewer", "nw-atlas-2#xhigh", "--author", "ts-3-core#max", "--json"],
    "frontier-review": ["--author", "ts-3-core#max", "--json"],
    "show-seats": ["--json"],
    "list-routes": ["--json"],
    "price-export": [],
    "admit-review": ["--author", "ts-3-core#max", "--usage-file", "@usage", "--base", "b", "--head", "h", "--json"],
    "emit-claude-agents": ["claude-agents"],
    "show-data": ["doctrine"],
    "lint-consumers": [],
}


class MalformedDataTest(unittest.TestCase):
    def test_every_command_names_the_row_and_raises_nothing(self):
        """Claim: with aliases written as a number, every command exits
        non-zero with the row's diagnostic and no Python exception escapes.
        Rejects a command that projects malformed rows and crashes, or one
        that reads empty projections and answers as if the roster were empty."""
        root = scratch(self, code=True)
        edit(root, stores.CATALOG, 'aliases = ["northwind-atlas-2"]', "aliases = 3")
        usage = root / "usage.json"
        usage.write_text(json.dumps({}))
        environment = {"AGENT_CODE_ROOT": str(root), "AGENT_HARNESS_BIN": "/bin/false"}
        for command, argv in COMMANDS.items():
            with self.subTest(command=command):
                argv = [str(usage) if value == "@usage" else value for value in argv]
                code, out, err = run_command(root / "bin" / command, argv, environment)
                output = out + err
                self.assertNotEqual(code, 0, output)
                self.assertIn(DIAGNOSTIC, output)


DECIDING = {
    "resolve-route": ["implement", "--backend", "pi", "--json"],
    "validate-selection": ["--profile", "implement", "--backend", "claude", "--model", "nw-atlas-2", "--effort",
                           "high", "--provider", "northwind-plan", "--reason", "fixture", "--json"],
    "assess-review": ["--reviewer", "nw-atlas-2#xhigh", "--author", "ts-3-core#max", "--json"],
    "frontier-review": ["--author", "orbit-flash#max", "--json"],
    "admit-review": ["--author", "ts-3-core#max", "--usage-file", "@usage", "--base", "b", "--head", "h", "--json"],
    "routing-check": ["nw-swift-2", "max"],
    "list-routes": ["--json"],
    "show-seats": ["--json"],
}


class OutsideTheDecidingPathTest(unittest.TestCase):
    """Guards and notes: no deciding verb reads them, and no fault in them makes one refuse."""

    def answers(self, root):
        usage = root / "usage.json"
        usage.write_text(json.dumps({"claude": {"state": "fresh", "updated_at": 2_000_000_000}}))
        environment = {"AGENT_CODE_ROOT": str(root)}
        out = {}
        for command, argv in DECIDING.items():
            argv = [str(usage) if value == "@usage" else value for value in argv]
            code, stdout, stderr = run_command(root / "bin" / command, argv, environment)
            out[command] = (code, re.sub(r"[0-9a-f]{12}", "VERSION", stdout + stderr))
        out["ladder"] = review_ladder.table_at(root, stores.texts_at(root))
        return out

    def test_a_faulty_guard_or_note_leaves_every_deciding_verb_answering(self):
        """Claim: a guard naming an unknown model, a guard whose rule is two
        sentences, and a notes line that is not JSON leave resolve, validate,
        assess, frontier, admit-review, check, routes, seats and the ladder
        answering exactly as before, while lint names the faulty row. Rejects
        a standing instruction or a field note that takes routing down."""
        expected = self.answers(scratch(self, code=True))
        self.assertTrue(all(code == 0 for code, _ in (value for key, value in expected.items() if key != "ladder")),
                        expected)
        cases = [
            (stores.POLICY, 'model = "orbit-flash"\neffort = "max"\nprofile = "implement"',
             'model = "orbit-nobody"\nprofile = "implement"',
             "data/policy.toml [[guard]] model=orbit-nobody profile=implement: model is not a catalog model"),
            (stores.POLICY, 'rule = "Name a wall-clock bound in every brief."',
             'rule = "Name a wall-clock bound. Check it in every brief."',
             "data/policy.toml [[guard]] model=orbit-flash effort=max profile=implement: rule is one sentence of at "
             "most 240 characters"),
            (stores.NOTES, None, "this line is not JSON\n", "data/notes.jsonl:3: Expecting value"),
        ]
        for store, old, new, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic):
                root = scratch(self, code=True)
                if old is None:
                    with (root / store).open("a") as handle:
                        handle.write(new)
                else:
                    edit(root, store, old, new)
                self.assertEqual(self.answers(root), expected)
                code, out, err = run_command(root / "bin" / "lint-routing", [], {})
                self.assertNotEqual(code, 0)
                self.assertTrue(any(line.startswith(diagnostic) for line in (out + err).splitlines()), out + err)

    def test_a_malformed_reference_is_a_diagnostic(self):
        """Claim: a guard whose `because` holds a table, and notes whose id,
        model, kind or effort is a list, each yield a diagnostic naming the
        row instead of raising. Rejects a reference check that runs before
        the shape it relies on is known."""
        root = scratch(self)
        edit(root, stores.POLICY, 'because = ["n0002"]', 'because = [{note = "n0002"}]')
        with (root / stores.NOTES).open("a") as handle:
            handle.write('{"id": ["n0009"], "date": "2030-01-06", "model": ["orbit-flash"], "effort": ["max"], '
                         '"kind": ["weakness"], "areas": ["latency"], "claim": "Slow.", "cause": ["unknown"], '
                         '"evidence": "fixture"}\n')
        import routing_profiles
        problems = routing_profiles.data_problems(root)
        self.assertIn("data/policy.toml [[guard]] model=orbit-flash effort=max profile=implement: because must be a "
                      "list of distinct nonblank strings, not [{'note': 'n0002'}]", problems)
        for key in ("id", "model", "effort", "kind", "cause"):
            self.assertTrue(any(f": {key} must be" in problem for problem in problems), (key, problems))


if __name__ == "__main__":
    unittest.main()
