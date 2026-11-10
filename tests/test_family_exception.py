"""A declared family exception lets one reviewer clear named same-family authors.

A `[[family_exception]]` row lifts `same-family` for exactly the pairs it
names and lists those authors under `family_exception`, outside the
qualifiers; every floor, the clearance floor and `same-model` still bind, and
lint keeps the rows meaningful.
"""

import pathlib
import shutil
import sys
import tempfile
import unittest

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "lib"))
sys.path.insert(0, str(REPOSITORY / "tests"))
from roster import ROOT  # noqa: E402

from routing_profiles import assess_review, validation_problems  # noqa: E402

FAMILY_ROW = '[[family]]\nid = "openai"\naliases = ["gpt-5.6", "gpt-5.5"]\n'
EXCEPTION_ROW = (
    '\n[[family_exception]]\nreviewer = "fable-5.2"\n'
    'authors = ["opus-5.5", "sonnet-5.5", "haiku-5.5"]\n'
    'note = "Directed by the operator on 2026-11-10."\n'
)


class FamilyExceptionTest(unittest.TestCase):
    def roster(self, row: str | None = EXCEPTION_ROW) -> pathlib.Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        shutil.copytree(ROOT / "routing", root / "routing")
        path = root / "routing" / "models.toml"
        text = path.read_text()
        self.assertIn(FAMILY_ROW, text)
        if row is not None:
            path.write_text(text.replace(FAMILY_ROW, FAMILY_ROW + row, 1))
        return root

    def test_an_excepted_reviewer_clears_a_named_same_family_author(self):
        # Claim: with the row, Fable 5.2 high clears Opus 5.5 xhigh work in a
        # form Arc records: a clearing assessment names no qualifier, and the
        # exception is said under `family_exception`. Rejects: a declared
        # exception that assess ignores, still reporting same-family and
        # leaving the debt owed; an exception carried as a qualifier, which
        # Arc refuses as outside its closed set; and, without the row, a pair
        # that clears anyway.
        excepted = assess_review(self.roster(), "fable-5.2#high", ["opus-5.5#xhigh"])
        self.assertEqual(excepted["qualifiers"], [])
        self.assertEqual(excepted["family_exception"], ["opus-5.5"])
        self.assertEqual(excepted["independence"], "eligible")
        self.assertIs(excepted["clears"], True)
        plain = assess_review(self.roster(None), "fable-5.2#high", ["opus-5.5#xhigh"])
        self.assertIn("same-family", plain["qualifiers"])
        self.assertNotIn("family_exception", plain)
        self.assertIs(plain["clears"], False)

    def test_the_exception_waives_neither_same_model_nor_floors(self):
        # Claim: the exception waives only the family. Rejects: Fable clearing
        # its own model's work, Fable low (rank 1) clearing Opus xhigh
        # (floor 2), or an author the row does not name riding on one it does.
        root = self.roster()
        own = assess_review(root, "fable-5.2#high", ["fable-5.2#medium"])
        self.assertIn("same-model", own["qualifiers"])
        self.assertIs(own["clears"], False)
        low = assess_review(root, "fable-5.2#low", ["opus-5.5#xhigh"])
        self.assertIn("below-floor", low["qualifiers"])
        self.assertIs(low["clears"], False)
        mixed = assess_review(root, "fable-5.2#high", ["opus-5.5#xhigh", "fable-5.1#high"])
        self.assertIn("same-family", mixed["qualifiers"])
        self.assertIs(mixed["clears"], False)

    def test_lint_refuses_a_meaningless_or_seated_exception(self):
        # Claim: lint holds each row to a reviewer outside the review seats
        # and authors of its own family. Rejects: an exception over a GPT
        # author, which would read as granting something; and one for a
        # seated review model, where resolve review and assess would disagree.
        self.assertEqual(validation_problems(self.roster()), [])
        cases = (
            (EXCEPTION_ROW.replace('"haiku-5.5"', '"gpt-6.1-sol"'), "is not of the reviewer's family"),
            (EXCEPTION_ROW.replace('reviewer = "fable-5.2"', 'reviewer = "opus-5.5"')
             .replace('"opus-5.5", ', '"fable-5.2", '), "holds a seat on the review profile"),
            (EXCEPTION_ROW.replace('"haiku-5.5"', '"fable-5.2"'), "cannot except its own model"),
            (EXCEPTION_ROW + EXCEPTION_ROW, "already named by another row"),
            (EXCEPTION_ROW.replace('note = "Directed by the operator on 2026-11-10."\n', ""),
             "exactly reviewer, authors and note"),
            (EXCEPTION_ROW.replace('"sonnet-5.5"', '"sonnet-55"'), "is not a roster model id"),
        )
        for row, problem in cases:
            with self.subTest(problem=problem):
                problems = validation_problems(self.roster(row))
                self.assertTrue(any(problem in found for found in problems), problems)


if __name__ == "__main__":
    unittest.main()
