"""The frozen roster the tests read, beside a copy of this repository's code.

`ROOT` is a temporary tree holding `tests/fixtures/roster` (the data) and
copies of `bin/`, `lib/`, `templates/` and the guide (the code). The CLIs
resolve their root from their own resolved path, so they must be copies:
a symlinked `bin/` would read the live roster. The tree is built once per
process and removed when the process exits.
"""

import atexit
import pathlib
import shutil
import tempfile

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = REPOSITORY / "tests" / "fixtures" / "roster"
CODE = ("bin", "lib", "templates", "doctrine/guide.md")


def build(root: pathlib.Path) -> pathlib.Path:
    """Write the fixture roster and this repository's code into `root`."""
    shutil.copytree(FIXTURE, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns("README.md"))
    for name in CODE:
        source, target = REPOSITORY / name, root / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return root


ROOT = build(pathlib.Path(tempfile.mkdtemp(prefix="agent-routing-roster-")))
atexit.register(shutil.rmtree, ROOT, ignore_errors=True)
