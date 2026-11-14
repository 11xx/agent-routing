"""Every command over malformed data: a diagnostic naming the row, never a traceback."""

import json
import unittest

from fixture import edit, run_command, scratch

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


if __name__ == "__main__":
    unittest.main()
