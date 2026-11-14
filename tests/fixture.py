"""The invented data set the tests read, beside a copy of this repository's code.

`FIXTURE` holds `data/` in the stores' own format: invented labs, models,
backends and pools, so a test asserts what the tool does and never what the
live roster says. `ROOT` is a temporary tree holding that data and copies of
the code. The CLIs resolve their root from their own resolved path, so they
must be copies: a symlinked `bin/` would read the live data. The tree is
built once per process and removed when the process exits.
"""

import atexit
import contextlib
import io
import os
import pathlib
import runpy
import shutil
import sys
import tempfile

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = REPOSITORY / "tests" / "fixtures" / "data"
CODE = ("bin", "lib", "templates", "doctrine/guide.md", "doctrine/principles.md", "DELEGATION.md")
sys.path.insert(0, str(REPOSITORY / "lib"))


def build(root: pathlib.Path, *, code: bool = True) -> pathlib.Path:
    """Write the fixture data, and unless told otherwise this repository's code, into `root`."""
    shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
    for name in CODE if code else ():
        source, target = REPOSITORY / name, root / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return root


def scratch(test, *, code: bool = False) -> pathlib.Path:
    """A private copy of the fixture data for one test to edit, removed after it."""
    temporary = tempfile.TemporaryDirectory()
    test.addCleanup(temporary.cleanup)
    return build(pathlib.Path(temporary.name), code=code)


def edit(root: pathlib.Path, store: str, old: str, new: str) -> None:
    """Replace one exact passage of a store; the passage must occur once."""
    path = root / store
    text = path.read_text()
    if text.count(old) != 1:
        raise AssertionError(f"{store}: expected one {old!r}, found {text.count(old)}")
    path.write_text(text.replace(old, new))


def run_command(script: pathlib.Path, argv: list[str], environment: dict | None = None) -> tuple[int, str, str]:
    """One command run in-process as its own __main__: its exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    saved = sys.argv, dict(os.environ)
    sys.argv = [str(script), *argv]
    os.environ.update(environment or {})
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exit_:
        code = exit_.code if isinstance(exit_.code, int) else 0 if exit_.code is None else 1
        if isinstance(exit_.code, str):
            err.write(exit_.code)
    finally:
        sys.argv = saved[0]
        os.environ.clear()
        os.environ.update(saved[1])
    return code, out.getvalue(), err.getvalue()


ROOT = build(pathlib.Path(tempfile.mkdtemp(prefix="agent-routing-fixture-")))
atexit.register(shutil.rmtree, ROOT, ignore_errors=True)
