import json
import os
import pathlib
import subprocess
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class ConsumerLintTest(unittest.TestCase):
    def config(self):
        with (ROOT / "routing" / "consumers.toml").open("rb") as handle:
            return tomllib.load(handle)

    def fixture_code_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        code = pathlib.Path(temporary.name)
        skills = self.config()["repository"]["skills"]
        instructions = code / "declared-harness"
        source_specs = [
            ("settings", instructions / "harnesses" / "pi" / "settings.json", ["roster-literals", "pi-route"]),
            ("shared-fragments", instructions / "shared" / "fragments", ["roster-literals", "agent-frontmatter"]),
            ("claude-fragments", instructions / "harnesses" / "claude" / "fragments", ["roster-literals", "agent-frontmatter"]),
            ("codex-fragments", instructions / "harnesses" / "codex" / "fragments", ["roster-literals", "agent-frontmatter"]),
            ("pi-fragments", instructions / "harnesses" / "pi" / "fragments", ["roster-literals", "agent-frontmatter"]),
            ("pi-agents", instructions / "harnesses" / "pi" / "agents", ["roster-literals", "agent-frontmatter"]),
            ("pi-subagent", instructions / "harnesses" / "pi" / "extensions" / "subagent", ["roster-literals", "agent-frontmatter"]),
        ]
        sources = [
            {"id": source_id, "path": str(path), "checks": checks}
            for source_id, path, checks in source_specs
        ]
        for _, path, _ in source_specs:
            if path.suffix:
                path.parent.mkdir(parents=True, exist_ok=True)
            else:
                path.mkdir(parents=True, exist_ok=True)
        harness = code / "agent-harness"
        harness.write_text(f"#!/usr/bin/env python3\nprint({json.dumps(sources)!r})\n")
        harness.chmod(0o700)
        self.harness = harness
        self.settings = instructions / "harnesses" / "pi" / "settings.json"
        skills_root = code / skills
        delegate_root = code / self.config()["repository"]["delegate"]
        self.proxy = delegate_root / "agents/codex.md"
        files = {
            str(self.settings): json.dumps({"$route": "interactive"}),
            str(self.proxy): "model: sonnet\neffort: low\n",
            str(delegate_root / "agents/pi.md"): "model: sonnet\neffort: low\n",
            str(delegate_root / "agents/opencode.md"): "model: sonnet\neffort: low\n",
            str(delegate_root / "agents/implement-opus.md"): "model: opus\neffort: medium\n",
        }
        directories = [
            f"{instructions}/fragments",
            f"{instructions}/agents",
            f"{instructions}/extensions/subagent",
            str(skills_root / "skills/retired-fixture"),
            str(delegate_root / "src"),
        ]
        for directory in directories:
            (code / directory).mkdir(parents=True)
        for relative, content in files.items():
            path = code / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return code

    def run_lint(self, code):
        environment = {
            **os.environ,
            "AI_AGENT_CODE_ROOT": str(code),
            "AGENT_HARNESS_BIN": str(self.harness),
        }
        return subprocess.run([ROOT / "bin" / "lint-consumers"], capture_output=True, text=True, env=environment)

    def test_clean_proxy_exception_is_exact(self):
        code = self.fixture_code_root()
        self.assertEqual(self.run_lint(code).returncode, 0)
        self.proxy.write_text("model: opus\neffort: low\n")
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("pins model frontmatter", result.stdout)

    def test_static_pi_default_is_rejected(self):
        code = self.fixture_code_root()
        self.settings.write_text(json.dumps({"defaultModel": "future-model"}))
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Pi default must use $route", result.stdout)

    def test_renamed_consumer_is_not_silently_dropped(self):
        code = self.fixture_code_root()
        instructions = self.settings.parents[2]
        self.settings.write_text(json.dumps({"defaultModel": "future-model"}))
        renamed = code / "renamed-consumer"
        instructions.rename(renamed)
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing delegation consumer", result.stdout)
        self.assertIn(str(instructions), result.stdout)
    def test_accessor_naming_nothing_is_a_failure(self):
        code = self.fixture_code_root()
        self.harness.write_text("#!/usr/bin/env python3\nprint('[]')\n")
        result = self.run_lint(code)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reported no delegation sources", result.stderr)


if __name__ == "__main__":
    unittest.main()
