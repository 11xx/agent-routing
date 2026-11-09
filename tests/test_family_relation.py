"""One family relation for review independence.

`assess` and `resolve review` read the same relation: a review seat that
`resolve` excludes as the author's family is one `assess` calls `same-family`,
so a read from it is never independent of that author and never clears.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "lib"))
sys.path.insert(0, str(REPOSITORY / "tests"))
from roster import ROOT  # noqa: E402

from routing_profiles import RouteRefusal, assess_review, resolve, validation_problems  # noqa: E402

FAMILY_ROW = '[[family]]\nid = "openai"\naliases = ["gpt-5.6", "gpt-5.5"]\n'


def review_seats() -> list[tuple[str | None, str, str]]:
    """Every review route as (variant, backend, reviewer coordinate)."""
    profiles = tomllib.loads((ROOT / "routing" / "profiles.toml").read_text())["profile"]
    review = next(profile for profile in profiles if profile["id"] == "review")
    return [
        (None if route is review else route["id"], route["backends"][0], f"{route['model']}#{route['effort']}")
        for route in [review, *review.get("variant", [])]
    ]


def rostered_families() -> dict[str, str]:
    """Each rostered model id with its own declared family."""
    models = tomllib.loads((ROOT / "routing" / "models.toml").read_text())["model"]
    return {model["id"]: model["family"] for model in models}


class OneFamilyRelationTest(unittest.TestCase):
    def test_a_gpt_5_6_author_is_of_sol_s_family(self):
        # Rejects: comparing raw family strings, which calls a GPT-5.6 author
        # independent of a GPT-6.1 Sol reviewer that the openai review route
        # excludes as that author's family, and lets the read clear.
        result = subprocess.run(
            [ROOT / "bin" / "agent-routing", "assess", "--reviewer", "gpt-6.1-sol#xhigh",
             "--author", "gpt-5.6-sol#high", "--json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        assessment = json.loads(result.stdout)
        self.assertIn("same-family", assessment["qualifiers"])
        self.assertEqual(assessment["independence"], "ineligible")
        self.assertIs(assessment["clears"], False)
        # The relation groups families; it does not rename the author's own.
        self.assertEqual(assessment["authors"][0]["family"], "gpt-5.6")

    def test_resolve_excludes_exactly_the_seats_assess_calls_same_family(self):
        # Rejects: a seat resolve fences off as the author's family that
        # assess still calls independent, or the reverse, for any rostered
        # author against any review route.
        for author, family in rostered_families().items():
            excluded, same_family = set(), set()
            for variant, backend, reviewer in review_seats():
                review = resolve(
                    ROOT, "review", backend, variant_id=variant, author=author, purpose="findings",
                    accept_ineligible=True, allow_cross_pool=True, allow_experimental=True,
                )["review"]
                if family in review["excluded_author_families"]:
                    excluded.add(variant)
                    self.assertEqual((review["independence"], review["clears"]), ("ineligible", False),
                                     (author, variant))
                qualifiers = assess_review(ROOT, reviewer, [author])["qualifiers"]
                if {"same-family", "same-model"} & set(qualifiers):
                    same_family.add(variant)
            with self.subTest(author=author):
                self.assertEqual(excluded, same_family)


class FamilyRelationManifestTest(unittest.TestCase):
    """The relation is declared once, in models.toml, and validation holds it to one partition."""

    def fixture_root(self, manifest: str, original: str, replacement: str) -> pathlib.Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        shutil.copytree(ROOT / "routing", root / "routing")
        path = root / "routing" / manifest
        self.assertIn(original, path.read_text())
        path.write_text(path.read_text().replace(original, replacement, 1))
        return root

    def test_both_readers_follow_the_declared_relation(self):
        # Rejects: a relation hard-coded in either reader, or a review route
        # that keeps excluding an author the manifest no longer groups with
        # its reviewer while assess calls the pair independent.
        root = self.fixture_root("models.toml", FAMILY_ROW, FAMILY_ROW.replace(', "gpt-5.5"', ""))
        self.assertEqual(validation_problems(root), [])
        assessment = assess_review(root, "gpt-6.1-sol#xhigh", ["gpt-5.5"])
        self.assertNotIn("same-family", assessment["qualifiers"])
        review = resolve(root, "review", "codex", author="gpt-5.5", accept_ineligible=True)["review"]
        self.assertEqual(review["excluded_author_families"], ["openai", "gpt-5.6"])

    def test_a_route_cannot_declare_exclusions_of_its_own(self):
        # Rejects: a review route whose own exclusion list could widen or
        # narrow the relation assess reads, silently accepted.
        anchor = 'id = "review"\n'
        root = self.fixture_root("profiles.toml", anchor, anchor + 'excluded_author_families = ["openai"]\n')
        self.assertIn("review: unknown key 'excluded_author_families'", validation_problems(root))

    def test_a_malformed_family_row_invalidates_the_manifest_and_refuses_assessment(self):
        # Rejects: a relation naming a lineage no model carries (a typo that
        # would quietly split a family), a lineage claimed by two families,
        # or a row of the wrong shape, read as though it were valid.
        cases = (
            ('aliases = ["gpt-5.6", "gpt-5.5"]', 'aliases = ["gpt-5.6", "gpt-55"]', "not a roster model family"),
            ('aliases = ["gpt-5.6", "gpt-5.5"]', 'aliases = [" gpt-5.6", "gpt-5.5"]', "not a roster model family"),
            ('aliases = ["gpt-5.6", "gpt-5.5"]', 'aliases = ["gpt-5.6", "gpt-5.5", "openai"]', "already names family"),
            (FAMILY_ROW, FAMILY_ROW + '\n[[family]]\nid = "claude"\naliases = ["gpt-5.5"]\n', "already names family"),
            ('aliases = ["gpt-5.6", "gpt-5.5"]', "aliases = []", "nonempty list"),
            ('aliases = ["gpt-5.6", "gpt-5.5"]', 'members = ["gpt-5.6"]', "exactly id and aliases"),
        )
        for original, replacement, problem in cases:
            with self.subTest(replacement=replacement):
                root = self.fixture_root("models.toml", original, replacement)
                self.assertTrue(any(problem in found for found in validation_problems(root)),
                                validation_problems(root))
                with self.assertRaises(RouteRefusal) as caught:
                    assess_review(root, "gpt-6.1-sol#xhigh", ["gpt-5.6-sol#high"])
                self.assertEqual(caught.exception.kind, "manifest-invalid")


if __name__ == "__main__":
    unittest.main()
