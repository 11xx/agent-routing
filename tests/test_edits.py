"""Store edits refuse before writing and leave a narrow, reversible Git account."""

import io
import json
import os
import pathlib
import subprocess
import sys
import threading
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from edit_fixture import GitStoreTest
import data_edits
import edit_cli
import stores
from routing_profiles import resolve


class EditTest(GitStoreTest):
    def test_refusal_atomic(self):
        """Claim: an unresolvable candidate is refused without byte or HEAD changes; rejects validating after write."""
        before = self.texts()
        with self.assertRaisesRegex(stores.StoreError, r"data/catalog.toml.*tier|data/policy.toml.*seat"):
            self.apply("prohibit", model="ts-3-core", effort="max", reason="The tier is unreliable.", why="Reject it.")
        self.assertEqual(self.texts(), before)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_accepted_edit_is_one_canonical_row_and_data_commit(self):
        """Claim: one seat changes canonically in a reasoned, data-only commit; rejects bundling staged source or row drift."""
        (self.root / "unrelated.txt").write_text("retain staged work\n")
        self.git("add", "unrelated.txt")
        before = self.texts()
        result = self.seat(because=["n0001"])
        self.assertEqual(len(result["changes"]), 1)
        row = result["changes"][0]
        self.assertEqual((row["store"], row["table"], row["before"]["effort"], row["after"]["effort"]),
                         (stores.POLICY, "seat", "max", "low"))
        self.assertEqual(stores.canonical_problems(self.root), [])
        self.assertEqual(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"), stores.POLICY)
        self.assertIn("A stronger tier catches the fixture defect.", self.git("log", "-1", "--format=%B"))
        self.assertIn("Because: n0001", self.git("log", "-1", "--format=%B"))
        self.assertIn("Routing-edit: set-seat", self.git("log", "-1", "--format=%B"))
        self.assertIn("Implemented-by: fixture:invented#high", self.git("log", "-1", "--format=%B"))
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "unrelated.txt")
        self.assertEqual(result["old_route_version"], stores.route_version(before))
        self.assertEqual(result["new_route_version"], stores.load(self.root).version)
        self.assertEqual(result["stale_consumers"], [])

    def review_seat(self, verb="set-review-seat", **opts):
        defaults = dict(purpose="clearance", author_family="orbit", backend="claude")
        if verb == "set-review-seat":
            defaults.update(model="nw-atlas-2", effort="xhigh", when="Independent review of orbit work.")
        return self.apply(verb, **{**defaults, "why": "The fixture names a reader for orbit authors.", **opts})

    def test_a_review_seat_edit_is_one_row_and_one_commit(self):
        """Claim: set-review-seat adds or updates exactly the row its purpose,
        author lab and backend name, in one data-only commit, and a later
        resolve answers from it. Rejects an edit keyed more loosely that
        rewrites another lab's seat, or one that leaves no commit."""
        result = self.review_seat()
        self.assertEqual([(row["table"], row["before"], row["after"]["author_family"]) for row in result["changes"]],
                         [("review_seat", None, "orbit")])
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "1")
        self.assertEqual(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"), stores.POLICY)
        message = self.git("log", "-1", "--format=%B")
        self.assertTrue(message.startswith("data: set clearance review seat for orbit on claude\n"), message)
        self.assertIn("Routing-edit: set-review-seat", message)
        self.assertEqual(resolve(self.root, "review", "claude", author="orbit-flash#max")["profile"], "review:atlas")
        removed = self.review_seat("remove-review-seat", why="The any seat serves orbit authors.")
        self.assertEqual([(row["before"]["author_family"], row["after"]) for row in removed["changes"]],
                         [("orbit", None)])
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "2")

    def test_removing_a_labs_only_clearance_seat_is_refused(self):
        """Claim: removing the only clearance seat outside a lab whose models
        hold seats is refused, naming the lab, with no byte or commit
        written; removing a seat that leaves every lab served succeeds.
        Rejects an edit that strands a lab's work without an independent
        reader."""
        before = self.texts()
        with self.assertRaisesRegex(stores.StoreError, "lab tessel has seated authors and no clearance seat outside"):
            self.review_seat("remove-review-seat", author_family="any", why="Drop the Northwind reader.")
        self.assertEqual((self.texts(), self.git("rev-parse", "HEAD")), (before, self.base))
        self.review_seat("remove-review-seat", purpose="findings", author_family="any", backend="pi",
                         why="Pi reads no findings.")
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "1")

    def test_reader_between_lock_and_rename(self):
        """Claim: a deciding reader during publication sees a complete old or new answer; rejects truncate-and-write."""
        entered, release = threading.Event(), threading.Event()
        original_replace = os.replace
        failure, result = [], []
        def replacing(source, target):
            # The old file remains complete while the replacement has already been flushed.
            if pathlib.Path(target).name == "policy.toml" and not entered.is_set():
                entered.set()
                self.assertEqual((self.root / stores.POLICY).read_text(), before[stores.POLICY])
                if not release.wait(2):
                    raise AssertionError("reader was not launched")
            return original_replace(source, target)
        def writer():
            try:
                result.append(self.seat())
            except BaseException as error:
                failure.append(error)
        before = self.texts()
        with patch.object(data_edits.os, "replace", side_effect=replacing):
            thread = threading.Thread(target=writer)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                source = ("import json,pathlib,sys; sys.path.insert(0,sys.argv[1]); "
                          "from routing_profiles import resolve; print('ready',flush=True); "
                          "print(json.dumps(resolve(pathlib.Path(sys.argv[2]),'implement','pi')))")
                reader = subprocess.Popen([sys.executable, "-c", source, str(pathlib.Path(stores.__file__).parent), str(self.root)],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.assertEqual(reader.stdout.readline().strip(), "ready")
                release.set()
                out, err = reader.communicate(timeout=2)
                self.assertEqual(reader.returncode, 0, err)
                self.assertIn(json.loads(out)["effort"], ("max", "low"))
            finally:
                release.set()
                thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failure, [])
        self.assertEqual(len(result), 1)

    def test_dirty_refuses(self):
        """Claim: staged and unstaged data edits refuse with recovery instructions; rejects overwriting operator edits."""
        for staged in (False, True):
            with self.subTest(staged=staged):
                path = self.root / stores.POLICY
                path.write_text(path.read_text() + "\n")
                if staged:
                    self.git("add", stores.POLICY)
                before = self.texts()
                with self.assertRaisesRegex(stores.StoreError, r"commit --why.*discard"):
                    self.seat()
                self.assertEqual(self.texts(), before)

    def test_dry_run_writes_nothing(self):
        """Claim: dry run validates and reports without any file or Git write beyond the empty lock file every
        reader opens; rejects a hidden commit, index or temporary write."""
        lock = pathlib.Path(".git") / "routing-data.lock"
        def snapshot():
            return {str(path.relative_to(self.root)): path.read_bytes()
                    for path in self.root.rglob("*") if path.is_file() and path.relative_to(self.root) != lock}
        before = snapshot()
        result = self.seat(dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertIsNone(result["commit"])
        self.assertNotEqual(result["old_route_version"], result["new_route_version"])
        self.assertEqual(snapshot(), before)
        self.assertEqual((self.root / lock).read_bytes(), b"")

    def test_undo_restores_bytes_and_answers(self):
        """Claim: undo restores previous policy bytes and resolution in a new commit; rejects a reset or incomplete inverse."""
        before = self.texts()
        answer = resolve(self.root, "implement", "pi")
        edit = self.seat()
        undo = self.apply("undo", why="Restore the previous verified seat.")
        self.assertEqual(undo["undone_commit"], edit["commit"])
        self.assertEqual(self.texts(), before)
        self.assertEqual(resolve(self.root, "implement", "pi"), answer)
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "2")

    def test_json_matches_text_facts(self):
        """Claim: one JSON object and text carry the same edit facts; rejects banners or dropped versions and rows."""
        options = ["set-seat", "implement", "--variant", "flat", "--backend", "pi", "--model", "orbit-flash",
                   "--effort", "low", "--when", "Specified work needs high.", "--why", "Use a stronger tier.", "--dry-run"]
        def run(extra):
            output, errors = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                code = edit_cli.main(self.root, [*options, *extra])
            self.assertEqual(code, 0, errors.getvalue())
            return output.getvalue()
        result = json.loads(run(["--json"]))
        text = run([])
        self.assertEqual(text.rstrip(), data_edits.render(result))
        self.assertIn(result["old_route_version"], text)
        self.assertIn(result["new_route_version"], text)
        for row in result["changes"]:
            for key, item in row["after"].items():
                if row["before"].get(key) != item:
                    self.assertIn(str(item), " ".join(text.split()))

    def test_commit_hand_edits_and_reject_notes_rewrite(self):
        """Claim: hand edits canonicalize and commit, while rewritten note history refuses; rejects using commit to erase evidence."""
        path = self.root / stores.POLICY
        path.write_text(path.read_text().replace('when = "Specified implementation from pi."', 'when = "A hand-edited scope."', 1) + "\n")
        result = self.apply("commit", why="Exercise a hand-edited seat.")
        self.assertEqual(stores.canonical_problems(self.root), [])
        self.assertEqual(result["changes"][0]["after"]["when"], "A hand-edited scope.")
        path = self.root / stores.NOTES
        path.write_text(path.read_text().replace("fixture", "changed", 1))
        before = self.texts()
        with self.assertRaisesRegex(stores.StoreError, "append-only"):
            self.apply("commit", why="Rewrite prior evidence.")
        self.assertEqual(self.texts(), before)

    def test_commit_failure_rolls_back(self):
        """Claim: a signing failure restores working bytes and staged work; rejects leaving an uncommitted applied edit."""
        before = self.texts()
        self.git("config", "commit.gpgsign", "true")
        self.git("config", "gpg.program", "does-not-exist-fixture")
        with self.assertRaises(stores.StoreError):
            self.seat()
        self.assertEqual(self.texts(), before)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)

    def test_default_fallback_guard_and_catalog(self):
        """Claim: each supported row edit takes effect and validates; rejects commands that report success without changing policy."""
        default = self.apply("default-seat", profile="implement", variant="atlas-high", backend=["claude"], why="Prefer deeper work.")
        self.assertIn("harness-agents", [row["consumer"] for row in default["stale_consumers"]])
        self.assertEqual(resolve(self.root, "implement", "claude")["effort"], "high")
        self.apply("set-fallback", profile="implement", from_provider="northwind-plan", backend="claude", variant="atlas-high", why="Use the declared recovery seat.")
        self.apply("remove-fallback", profile="implement", from_provider="northwind-plan", backend="claude", why="Retire this recovery seat.")
        self.apply("set-guard", model="ts-3-core", effort="max", rule="Name a deadline.", why="Bound the work.", because=["n0001"])
        guard = next(row for row in stores.load(self.root).policy["guard"] if row["model"] == "ts-3-core")
        self.assertEqual(guard["because"], ["n0001"])
        self.apply("set-guard", model="ts-3-core", effort="max", rule="Name a hard deadline.", why="Keep the bound explicit.")
        self.apply("retire-guard", model="ts-3-core", effort="max", why="The caller enforces the deadline.")
        self.apply("remove-seat", profile="implement", variant="trial", why="Retire the trial seat.")
        self.apply("supersede-model", model="orbit-trial", successor="orbit-flash", why="Prefer the measured successor.")
        self.apply("prohibit", model="nw-swift-2", effort="max", reason="Keep the trial capped.", why="No measured benefit.")
        self.apply("allow", model="nw-swift-2", effort="max", why="Permit explicit trials.")
        result = self.apply("rank", model="ts-3-core", effort="low", rank=1, floor=2, why="Raise the author floor.")
        self.assertIn("Arc assurance at once", result["notice"])
        self.assertEqual(data_edits.candidate_problems(self.texts()), [])

    def test_undo_conflict_and_disjoint_later_hand_edit(self):
        """Claim: undo merges disjoint later edits and refuses overlap; rejects replacing the whole store with history."""
        self.seat()
        path = self.root / stores.POLICY
        path.write_text(path.read_text().replace("a read-only survey of a source tree", "a scoped survey of a source tree", 1))
        self.git("add", stores.POLICY)
        self.git("commit", "--quiet", "-m", "Adjust an unrelated header")
        self.apply("undo", why="Restore the earlier seat only.")
        self.assertEqual(resolve(self.root, "implement", "pi")["effort"], "max")
        self.assertIn("a scoped survey of a source tree", path.read_text())
        # A conflicting change is a plain commit, not itself an edit-verb target.
        self.seat()
        path.write_text(path.read_text().replace('when = "Specified work needs high."', 'when = "A conflicting scope."'))
        self.git("add", stores.POLICY)
        self.git("commit", "--quiet", "-m", "Change the same seat by hand")
        before = self.texts()
        with self.assertRaisesRegex(stores.StoreError, "conflicts"):
            self.apply("undo", why="Reject the conflicting inverse.")
        self.assertEqual(self.texts(), before)

    def test_promote_variant_retains_primary(self):
        """Claim: promoting a variant retains the primary route by name; rejects unreachable defaults or deleting its seat."""
        self.apply("set-seat", profile="implement", variant="alternate", backend=["codex"], model="ts-3-core", effort="max",
                   when="Alternate scope on the same window.", why="Keep the tuple available by name.")
        self.apply("default-seat", profile="implement", variant="alternate", backend=["codex"], why="Prefer the alternate scope.")
        answer = resolve(self.root, "implement", "codex")
        self.assertEqual(answer["profile"], "implement:alternate")
        retained = resolve(self.root, "implement", "codex", variant_id="primary-codex")
        self.assertEqual((retained["model"], retained["effort"]), (answer["model"], answer["effort"]))
        self.assertEqual(data_edits.candidate_problems(self.texts()), [])

    def test_removing_default_refuses(self):
        """Claim: removing the only default for a backend refuses; rejects leaving an unnamed request unresolvable."""
        before = self.texts()
        with self.assertRaisesRegex(stores.StoreError, "resolvable default"):
            self.apply("remove-seat", profile="implement", variant="flat", why="Remove a backend default.")
        self.assertEqual(self.texts(), before)
