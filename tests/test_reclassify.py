"""An edit of pool ranks lists exactly the directed selections whose classification validate changes."""

import concurrent.futures
import pathlib
import shutil
import tempfile

from test_page import SEAT, PageServerTest
import data_edits
import stores
from routing_profiles import RouteRefusal, validate_selection

TOP = ["pool-rank", "ts-3-prime", "xhigh", "--pool", "tessel-plan", "--rank", "1", "--why", "Planning yields the top of the pool."]
SAGE = ["set-seat", "plan", "--variant", "sage", "--backend", "claude", "--model", "nw-atlas-2", "--effort", "low",
        "--provider", "northwind-plan", "--pool-rank", "2", "--when", "Planning from a Northwind session.",
        "--why", "The head model's low tier plans."]
CLASS = ("direction", "stability", "selection_kind")


def answers(root):
    """validate's classification of every selection the fixture can name: each profile, backend, model tier and pool."""
    loaded = stores.load(root)
    classes = {}
    for profile in loaded.profiles:
        for backend in loaded.backends:
            for model in loaded.models:
                for tier in model["effort"]:
                    for pool in loaded.pools:
                        key = (profile["id"], backend["id"], model["id"], tier["effort"], pool["provider"])
                        try:
                            answer = validate_selection(root, *key, "Compare the classification.", allow_experimental=True)
                        except RouteRefusal:
                            continue
                        classes[key] = {name: answer[name] for name in CLASS}
    return classes


def changed(before, after):
    return sorted((key, before[key], after[key]) for key in before.keys() & after.keys() if before[key] != after[key])


def listed(result):
    return sorted(((row["profile"], row["backend"], row["model"], row["effort"], row["pool"]), row["before"], row["after"])
                  for row in result["classification_changes"])


class ReclassifyTest(PageServerTest):
    def test_the_list_is_every_selection_validate_reclassifies_and_no_other(self):
        """Claim: the preview and the commit of an edit of pool ranks list
        exactly the selections validate answers both before and after it
        and classifies differently, over every profile, backend, model tier
        and pool of the fixture; a selection validate refuses either way is
        not listed. Rejects a list from the classifier alone, which counts a
        tier its backend cannot run."""
        scratch = tempfile.TemporaryDirectory(dir=self.root.parent)
        self.addCleanup(scratch.cleanup)
        copies, results = [], []
        def keep():
            copy = pathlib.Path(scratch.name) / str(len(copies))
            shutil.copytree(self.root / "data", copy / "data")
            copies.append(copy)
        keep()
        for argv in (SAGE, TOP):
            status, preview = self.edit(argv)
            self.assertEqual(status, 200, preview)
            status, answer = self.edit(argv, confirm=True, expect=preview["stamp"])
            self.assertEqual(status, 200, answer)
            results.append((argv[:2], preview["result"], answer["result"]))
            keep()
        with concurrent.futures.ProcessPoolExecutor(len(copies)) as pool:
            swept = list(pool.map(answers, copies))
        for (verb, previewed, committed), before, after in zip(results, swept, swept[1:]):
            expected = changed(before, after)
            self.assertTrue(expected)
            self.assertEqual((listed(previewed), listed(committed)), (expected, expected), verb)
        refused = ("survey", "pi", "ts-3-prime", "xhigh", "tessel-plan")
        with self.assertRaises(RouteRefusal) as raised:
            validate_selection(self.root, *refused, "Probe the refusal.", allow_experimental=True)
        self.assertEqual(raised.exception.kind, "unsupported-effort")
        self.assertNotIn(refused, [row[0] for row in listed(answer["result"])])

    def test_the_text_and_the_page_say_what_moved_or_that_nothing_did(self):
        """Claim: text names each reclassified selection with its direction,
        stability and kind before and after, says none when a rank edit
        reclassifies nothing, and an edit of no rank carries no list.
        Rejects a rank move whose effect the preview hides."""
        status, preview = self.edit(SAGE)
        self.assertEqual(status, 200, preview)
        self.assertIn("plan on claude: nw-atlas-2 xhigh via northwind-plan: downgrade (experimental, operator-directed) → "
                      "upgrade (stable, operator-escalation)", " ".join(data_edits.render(preview["result"], width=400).split()))
        quiet = data_edits.apply(self.root, "pool-rank", dry_run=True, model="nw-sage-2", effort="high",
                                 pool="northwind-plan", rank=6, why="The top of the pool stays the top.")
        self.assertEqual(quiet["classification_changes"], [])
        self.assertIn("directed selections reclassified: none", data_edits.render(quiet))
        status, plain = self.edit(SEAT)
        self.assertNotIn("classification_changes", plain["result"])
