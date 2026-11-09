import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import tomllib
import sys
import unittest

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "lib"))
sys.path.insert(0, str(REPOSITORY / "tests"))
from roster import ROOT  # noqa: E402
from claude_agents import claude_agent_bundle


class ConsumerLintTest(unittest.TestCase):
    def config(self):
        with (ROOT / "routing" / "consumers.toml").open("rb") as handle:
            return tomllib.load(handle)

    def fixture_code_root(self):
        worktrees = pathlib.Path.home() / ".worktrees"
        worktrees.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=worktrees)
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
            str(self.proxy): "model: opus\neffort: low\n",
            str(delegate_root / "agents/pi.md"): "model: opus\neffort: low\n",
            str(delegate_root / "agents/opencode.md"): "model: opus\neffort: low\n",
        }
        implementers = claude_agent_bundle(ROOT, profile_id="implement")["files"]
        for name, content in implementers.items():
            if name.startswith("agents/"):
                files[str(delegate_root / name)] = content
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
            "AGENT_CODE_ROOT": str(code),
            "AGENT_HARNESS_BIN": str(self.harness),
        }
        return subprocess.run([ROOT / "bin" / "lint-consumers"], capture_output=True, text=True, env=environment)

    def test_linked_worktree_discovers_siblings_without_an_override(self):
        code = self.fixture_code_root()
        canonical = code / "agent-routing"
        canonical.mkdir()
        for directory in ("bin", "lib", "routing", "templates"):
            shutil.copytree(ROOT / directory, canonical / directory,
                            ignore=shutil.ignore_patterns("__pycache__"))
        subprocess.run(["git", "init", "-q", str(canonical)], check=True)
        subprocess.run(["git", "-C", str(canonical), "add", "bin", "lib", "routing", "templates"], check=True)
        subprocess.run(["git", "-C", str(canonical), "-c", "commit.gpgsign=false",
                        "commit", "-qm", "fixture"], check=True)
        worktree = code / "isolated" / "routing-worktree"
        subprocess.run(["git", "-C", str(canonical), "worktree", "add", "--quiet",
                        "--detach", str(worktree)], check=True)
        environment = {**os.environ, "AGENT_HARNESS_BIN": str(self.harness)}
        environment.pop("AGENT_CODE_ROOT", None)
        for root in (canonical, worktree):
            with self.subTest(root=root):
                result = subprocess.run([root / "bin/lint-consumers"], cwd=code,
                                        capture_output=True, text=True, env=environment)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.proxy.unlink()
        result = subprocess.run([worktree / "bin/lint-consumers"],
                                capture_output=True, text=True, env=environment)
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing delegation proxy", result.stdout)

    def test_clean_proxy_exception_is_exact(self):
        code = self.fixture_code_root()
        self.assertEqual(self.run_lint(code).returncode, 0)
        self.proxy.write_text("model: sonnet\neffort: low\n")
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("pins model frontmatter", result.stdout)

    def test_generated_native_trial_is_registered_by_the_roster(self):
        code = self.fixture_code_root()
        bundle = claude_agent_bundle(ROOT, profile_id="computer-use", variant_id="opus", allow_experimental=True)
        path = self.proxy.parent / "computer-use-opus.md"
        path.write_text(bundle["files"]["agents/computer-use-opus.md"])
        self.assertEqual(self.run_lint(code).returncode, 0)
        path.write_text(path.read_text().replace("effort: medium", "effort: max"))
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("generated agent differs", result.stdout)
        self.assertIn("centrally recorded effort", result.stdout)

    def test_generated_definition_body_drift_is_rejected(self):
        code = self.fixture_code_root()
        path = self.proxy.parent / "implement-opus-low.md"
        path.write_text(path.read_text() + "Do unrelated work.\n")
        result = self.run_lint(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("generated agent differs", result.stdout)

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
        self.assertIn("missing expected delegation sources", result.stderr)

    def test_accessor_reporting_fewer_sources_than_the_floor_is_a_failure(self):
        code = self.fixture_code_root()
        floor = self.config()["accessor"][0]["expected_sources"]
        self.assertGreater(len(floor), 1)
        sources = json.loads(subprocess.run([self.harness], capture_output=True, text=True).stdout)
        kept = [source for source in sources if source["id"] != floor[-1]]
        self.assertEqual(len(kept), len(sources) - 1)
        self.harness.write_text(f"#!/usr/bin/env python3\nprint({json.dumps(kept)!r})\n")
        result = self.run_lint(code)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing expected delegation sources", result.stderr)
        self.assertIn(floor[-1], result.stderr)

    def test_accessor_reporting_more_sources_than_the_floor_passes(self):
        code = self.fixture_code_root()
        floor = set(self.config()["accessor"][0]["expected_sources"])
        sources = json.loads(subprocess.run([self.harness], capture_output=True, text=True).stdout)
        self.assertTrue(floor < {source["id"] for source in sources})
        self.assertEqual(self.run_lint(code).returncode, 0)

    def test_an_accessor_without_a_declared_floor_is_a_failure(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        for directory in ("bin", "lib", "routing", "templates"):
            shutil.copytree(ROOT / directory, root / directory)
        path = root / "routing" / "consumers.toml"
        lines = path.read_text().splitlines(keepends=True)
        path.write_text("".join(line for line in lines if not line.startswith("expected_sources")))
        self.assertNotIn("expected_sources", path.read_text())
        code = self.fixture_code_root()
        result = subprocess.run(
            [root / "bin" / "lint-consumers"],
            capture_output=True,
            text=True,
            env={**os.environ, "AGENT_CODE_ROOT": str(code), "AGENT_HARNESS_BIN": str(self.harness)},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("declares no expected_sources floor", result.stderr)

    def test_an_empty_consumer_inventory_is_a_failure(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        for directory in ("bin", "routing"):
            shutil.copytree(ROOT / directory, root / directory)
        (root / "routing" / "consumers.toml").write_text(
            '[repository]\nskills = "agent-harnesses"\ndelegate = "agent-delegate"\n'
        )
        result = subprocess.run(
            [root / "bin" / "lint-consumers"],
            capture_output=True,
            text=True,
            env={**os.environ, "AGENT_CODE_ROOT": str(root / "code")},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("declares no delegation consumer", result.stderr)


if __name__ == "__main__":
    unittest.main()
