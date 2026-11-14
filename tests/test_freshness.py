"""What a preview showed is what its confirmation commits, and what a rank move does to directed selections."""

import contextlib
from unittest.mock import patch

from test_page import SEAT, PageServerTest
import data_edits
import routing_page
import stores
from routing_profiles import validate_selection

RANK = ["pool-rank", "nw-atlas-2", "xhigh", "--pool", "northwind-plan", "--rank", "6", "--why",
        "Review outranks planning in the Northwind pool."]
MOVED = dict(model="nw-atlas-2", effort="xhigh", pool="northwind-plan", rank=5, why="Another session moved it.")
SAGE = dict(profile="plan", variant="sage", backend=["claude"], model="nw-atlas-2", effort="low", provider="northwind-plan",
            when="Planning from a Northwind session.", why="The head model's low tier plans.")


def rank_of(root, model, effort, pool):
    return next(row["rank"] for row in stores.load(root).policy["seat_rank"]
                if (row["model"], row["effort"], row["pool"]) == (model, effort, pool))


class FreshnessTest(PageServerTest):
    def test_a_confirmation_from_a_moved_state_is_refused_wherever_the_move_lands(self):
        """Claim: an edit made by another writer after a preview, landing
        just before the confirmation's transaction or between the preview's
        computation and its stamp, makes the confirmation answer that the
        stores moved and write nothing; the library refuses an expected
        state that is not the current one. Rejects checking freshness
        outside the edit's own lock hold, or stamping a preview from a
        later read than the one it was computed on."""
        status, preview = self.edit(RANK)
        self.assertEqual(status, 200, preview)
        landed = []
        real_lock = stores.store_lock

        @contextlib.contextmanager
        def lock(root, *, exclusive=True):
            if exclusive and not landed:
                landed.append(None)
                landed[0] = data_edits.apply(self.root, "pool-rank", **MOVED)["commit"]
            with real_lock(root, exclusive=exclusive):
                yield

        with patch.object(stores, "store_lock", lock):
            status, answer = self.edit(RANK, confirm=True, expect=preview["stamp"])
        self.assertEqual((status, answer.get("stale")), (409, True), answer)
        self.assertEqual((self.git("rev-parse", "HEAD"), rank_of(self.root, "nw-atlas-2", "xhigh", "northwind-plan")),
                         (landed[0], 5))

        real_execute = routing_page.edit_cli.execute
        def execute(root, verb, args):
            answer = real_execute(root, verb, args)
            if args.get("dry_run"):
                data_edits.apply(self.root, "pool-rank", **dict(MOVED, rank=4, why="It moved back."))
            return answer
        with patch.object(routing_page.edit_cli, "execute", execute):
            status, preview = self.edit(RANK)
        self.assertEqual(preview["result"]["changes"][0]["before"]["rank"], 5)
        status, answer = self.edit(RANK, confirm=True, expect=preview["stamp"])
        self.assertEqual((status, answer.get("stale")), (409, True), answer)
        self.assertEqual(rank_of(self.root, "nw-atlas-2", "xhigh", "northwind-plan"), 4)

        texts, head = self.texts(), self.git("rev-parse", "HEAD")
        with self.assertRaises(data_edits.StaleState):
            data_edits.apply(self.root, "pool-rank", expect=preview["result"]["state"], **dict(MOVED, rank=6))
        self.unchanged(texts, head)
        state = data_edits.apply(self.root, "pool-rank", dry_run=True, **dict(MOVED, rank=6))["state"]
        self.assertEqual(data_edits.apply(self.root, "pool-rank", expect=state, **dict(MOVED, rank=6))["state"], state)

    def test_an_undo_confirms_only_the_commit_it_previewed(self):
        """Claim: an undo previewed before later verb edits is refused at
        confirmation even when those edits restore the same store bytes,
        and an undo naming its commit refuses once that commit is no longer
        the latest verb edit. Rejects freshness by store bytes alone, which
        would undo a different commit than the one previewed."""
        self.verb(*SEAT)
        seat = self.git("rev-parse", "HEAD")
        status, named = self.edit(["undo", "--commit", seat, "--why", "Back to max."])
        self.assertEqual((status, named["result"]["undone_commit"]), (200, seat))
        status, unnamed = self.edit(["undo", "--why", "Back to max."])
        self.assertEqual(status, 200)
        texts = self.texts()
        scope = ["nw-swift-2", "--effort", "high"]
        self.verb("set-guard", *scope, "--rule", "Name the fixture deadline.", "--why", "A probe needs a bound.")
        self.verb("retire-guard", *scope, "--why", "The probe ended.")
        self.assertEqual(self.texts(), texts)
        head = self.git("rev-parse", "HEAD")
        for argv, preview in ((["undo", "--commit", seat, "--why", "Back to max."], named),
                              (["undo", "--why", "Back to max."], unnamed)):
            status, answer = self.edit(argv, confirm=True, expect=preview["stamp"])
            self.assertEqual((status, answer.get("stale")), (409, True), answer)
        self.unchanged(texts, head)
        with self.assertRaisesRegex(data_edits.StaleState, f"the latest verb edit is {head[:12]}, not {seat[:12]}"):
            data_edits.apply(self.root, "undo", target=seat, why="Back to max.")
        self.unchanged(texts, head)

    def test_a_rank_move_lists_the_selections_it_reclassifies(self):
        """Claim: an edit that changes pool ranks lists every directed
        selection in those pools whose classification by validate changes,
        with its direction, stability and kind before and after, in JSON,
        text and the page's preview, or says none changes; an edit that
        changes no rank lists nothing. Rejects a rank move whose effect on
        directed selections the preview hides."""
        status, preview = self.edit(["set-seat", "plan", "--variant", "sage", "--backend", "claude", "--model", "nw-atlas-2",
                                     "--effort", "low", "--provider", "northwind-plan", "--pool-rank", "2",
                                     "--when", SAGE["when"], "--why", SAGE["why"]])
        self.assertEqual(status, 200, preview)
        listed = preview["result"]["classification_changes"]
        def judged(row):
            answer = validate_selection(self.root, row["profile"], row["backend"], row["model"], row["effort"],
                                        row["pool"], "Compare the classification.", allow_experimental=True)
            return {key: answer[key] for key in ("direction", "stability", "selection_kind")}
        before = [judged(row) for row in listed]
        result = data_edits.apply(self.root, "set-seat", pool_rank=2, **SAGE)
        self.assertEqual(result["classification_changes"], listed)
        self.assertEqual([row["before"] for row in listed], before)
        self.assertEqual([row["after"] for row in listed], [judged(row) for row in listed])
        self.assertIn(("downgrade", "upgrade"), [(row["before"]["direction"], row["after"]["direction"]) for row in listed
                                                 if (row["profile"], row["model"], row["effort"]) == ("plan", "nw-atlas-2", "xhigh")])
        self.assertIn("plan on claude: nw-atlas-2 xhigh via northwind-plan: downgrade (experimental, operator-directed) → "
                      "upgrade (stable, operator-escalation)", " ".join(data_edits.render(result, width=400).split()))
        quiet = data_edits.apply(self.root, "pool-rank", dry_run=True, model="nw-atlas-2", effort="xhigh",
                                 pool="northwind-plan", rank=5, why="Probe the top of the pool.")
        self.assertEqual(quiet["classification_changes"], [])
        self.assertIn("directed selections reclassified: none", data_edits.render(quiet))
        status, plain = self.edit(SEAT)
        self.assertNotIn("classification_changes", plain["result"])
