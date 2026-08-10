import json
import os
import pathlib
import subprocess
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class ConsumerLintTest(unittest.TestCase):
    def repository(self, name):
        with (ROOT / "routing" / "consumers.toml").open("rb") as handle:
            return tomllib.load(handle)["repository"][name]

    def fixture_code_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        code = pathlib.Path(temporary.name)
        instructions = self.repository("instructions")
        skills = self.repository("skills")
        files = {
            f"{instructions}/config/pi-settings.json": json.dumps({"$route": "interactive"}),
            f"{skills}/skills/codex-delegate/agents/codex.md": "model: sonnet\neffort: low\n",
            f"{skills}/skills/pi-delegate/agents/pi.md": "model: sonnet\neffort: low\n",
            f"{skills}/skills/opencode-delegate/agents/opencode.md": "model: sonnet\neffort: low\n",
        }
        directories = [
            f"{instructions}/fragments",
            f"{instructions}/agents",
            f"{instructions}/extensions/subagent",
            f"{skills}/skills/plan-for-codex",
            f"{skills}/skills/multi-wargame",
        ]
        for directory in directories:
            (code / directory).mkdir(parents=True)
        for relative, content in files.items():
            path = code / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return code

    def run_lint(self, code):
        environment = {**os.environ, "AI_AGENT_CODE_ROOT": str(code)}
        return subprocess.run([ROOT / "bin" / "lint-consumers"], capture_output=True, text=True, env=environment)

    def test_clean_proxy_exception_is_exact(self):
        code = self.fixture_code_root()
        self.assertEqual(self.run_lint(code).returncode, 0)
        proxy = code / "ai-agent-skills/skills/codex-delegate/agents/codex.md"
        proxy.write_text("model: opus\neffort: low\n")
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("pins model frontmatter", result.stdout)

    def test_static_pi_default_is_rejected(self):
        code = self.fixture_code_root()
        settings = code / self.repository("instructions") / "config/pi-settings.json"
        settings.write_text(json.dumps({"defaultModel": "future-model"}))
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Pi default must use $route", result.stdout)

    def test_renamed_consumer_is_not_silently_dropped(self):
        code = self.fixture_code_root()
        instructions = code / self.repository("instructions")
        (instructions / "config/pi-settings.json").write_text(json.dumps({"defaultModel": "future-model"}))
        renamed = code / "renamed-consumer"
        instructions.rename(renamed)
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing delegation consumer", result.stdout)
        self.assertIn(str(instructions), result.stdout)


if __name__ == "__main__":
    unittest.main()
