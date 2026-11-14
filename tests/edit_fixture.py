"""Small invented Git stores for edit acceptance tests."""

import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from fixture import build
import data_edits
import stores


class GitStoreTest(unittest.TestCase):
    def setUp(self):
        directory = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "agent-routing" / "edit-tests"
        directory.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(temporary.cleanup)
        self.root = build(pathlib.Path(temporary.name), code=False)
        environment = patch.dict(os.environ, dict(GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                                                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
                                                   GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"))
        environment.start()
        self.addCleanup(environment.stop)
        self.git("init", "--quiet", "--template=")
        self.git("add", "data")
        self.git("commit", "--quiet", "-m", "Establish invented stores")
        self.base = self.git("rev-parse", "HEAD")
        identity = patch.object(data_edits, "attribution", return_value="fixture:invented#high")
        self.identity_patch = identity
        identity.start()
        self.addCleanup(identity.stop)

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def texts(self):
        return data_edits.read_texts(self.root)

    def apply(self, verb, **opts):
        return data_edits.apply(self.root, verb, **opts)

    def seat(self, **opts):
        return self.apply("set-seat", **{**dict(profile="implement", variant="flat", backend=["pi"],
                                              model="orbit-flash", effort="low", when="Specified work needs high.",
                                              why="A stronger tier catches the fixture defect."), **opts})

    def note(self, **opts):
        return self.apply("note", **{**dict(model="ts-3-core", effort="max", kind="strength", areas=["implementation"],
                                          claim="Completed the fixture probe.", cause="executor", evidence="fixture:one",
                                          date="2030-02-01"), **opts})
