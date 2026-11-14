"""A seat edit carries the pool rank of the tier it seats, and drops the rank it strands, in one commit."""

from edit_fixture import GitStoreTest
import data_edits
import stores
from routing_profiles import resolve, validate_selection

MOVE = dict(profile="implement", backend=["codex"], model="ts-3-prime", effort="high", provider="tessel-plan",
            when="Specified implementation on the Tessel window.", why="The stronger tier lands the harder slices.")


def ranks(root):
    return {(row["model"], row["effort"], row["pool"]): row["rank"]
            for row in stores.load(root).policy.get("seat_rank", [])}


class PoolRankTest(GitStoreTest):
    def unchanged(self, texts):
        self.assertEqual(self.texts(), texts)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_moving_onto_an_unranked_tier_without_its_pool_rank_is_refused(self):
        """Claim: moving a stable seat onto a tier its pool has not ranked,
        without --pool-rank, is refused with the flag to pass, the pool's
        order and a suggested place, and writes nothing. Rejects a refusal
        that leaves the operator to find and hand-edit the seat_rank table."""
        texts = self.texts()
        with self.assertRaises(stores.StoreError) as raised:
            self.apply("set-seat", **MOVE)
        message = str(raised.exception)
        self.assertIn("ts-3-prime high has no pool rank on 'tessel-plan'; pass --pool-rank N", message)
        self.assertIn("ts-3-core max 2", message)
        self.assertIn("--pool-rank 2 keeps the place ts-3-core max held", message)
        self.unchanged(texts)

    def test_the_seat_and_its_pool_rank_land_in_one_commit(self):
        """Claim: with --pool-rank the moved seat, the new tier's rank and
        the removal of the rank its old tier no longer needs land in one
        commit, and resolve and validate answer from them. Rejects writing
        the rank separately, keeping a stranded rank, or ignoring the
        number given."""
        result = self.apply("set-seat", pool_rank=3, **MOVE)
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "1")
        rows = {(row["table"], bool(row["before"]), bool(row["after"])): row for row in result["changes"]}
        self.assertEqual(sorted(rows), [("seat", True, True), ("seat_rank", False, True), ("seat_rank", True, False)])
        self.assertEqual(rows["seat_rank", False, True]["after"],
                         dict(model="ts-3-prime", effort="high", pool="tessel-plan", rank=3))
        self.assertEqual(rows["seat_rank", True, False]["before"]["effort"], "max")
        self.assertIn("seat_rank ts-3-prime high tessel-plan added", data_edits.render(result))
        self.assertEqual(ranks(self.root).get(("ts-3-prime", "high", "tessel-plan")), 3)
        self.assertNotIn(("ts-3-core", "max", "tessel-plan"), ranks(self.root))
        route = resolve(self.root, "implement", "codex")
        self.assertEqual((route["model"], route["effort"]), ("ts-3-prime", "high"))
        selection = validate_selection(self.root, "implement", "codex", "ts-3-prime", "xhigh", "tessel-plan",
                                       "Compare with the new seat.")
        self.assertEqual(selection["direction"], "lateral")

    def test_removing_the_last_seat_on_a_tier_removes_its_stranded_rank(self):
        """Claim: removing the only stable seat on a tier also removes that
        tier's pool rank, in the same commit, and the result lists it.
        Rejects an edit that validation refuses for the rank it left
        behind."""
        result = self.apply("remove-seat", profile="implement", variant="atlas-high",
                            why="The head model's medium tier is enough.")
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "1")
        self.assertEqual([(row["table"], row["before"]["effort"], row["after"]) for row in result["changes"]],
                         [("seat", "high", None), ("seat_rank", "high", None)])
        self.assertNotIn(("nw-atlas-2", "high", "northwind-plan"), ranks(self.root))

    def test_a_pool_rank_changes_alone(self):
        """Claim: pool-rank changes one seated tier's rank and nothing
        else, a seat edit given --pool-rank on a ranked tier changes that
        rank, and a tier with no rank is refused with the edit that gives
        it one. Rejects a rank change that rewrites the seat or adds an
        unseated rank."""
        result = self.apply("pool-rank", model="ts-3-core", effort="high", pool="tessel-plan", rank=2,
                            why="Surveys outrank fixed-shape calls.")
        self.assertEqual([(row["table"], row["before"]["rank"], row["after"]["rank"]) for row in result["changes"]],
                         [("seat_rank", 1, 2)])
        self.assertTrue(self.git("log", "-1", "--format=%s").startswith("data: set pool rank for ts-3-core high on tessel-plan"))
        with self.assertRaisesRegex(stores.StoreError, "set-seat --pool-rank"):
            self.apply("pool-rank", model="ts-3-prime", effort="high", pool="tessel-plan", rank=2, why="Rank it.")
        seat = self.apply("set-seat", profile="survey", backend=["codex", "pi"], model="ts-3-core", effort="high",
                          provider="tessel-plan", pool_rank=1, when="Surveys from a Tessel or pi session.",
                          why="Surveys sit with fixed-shape calls again.")
        self.assertIn(("seat_rank", 2, 1), [(row["table"], row["before"].get("rank"), row["after"].get("rank"))
                                            for row in seat["changes"]])

    def test_undo_restores_the_seat_and_both_pool_ranks(self):
        """Claim: undoing a seat move restores the seat, the rank it
        removed and the absence of the rank it added, byte for byte.
        Rejects an undo that reverts the seat and leaves the ranks moved."""
        before = self.texts()
        self.apply("set-seat", pool_rank=2, **MOVE)
        self.apply("undo", why="Back to the workhorse.")
        self.assertEqual(self.texts(), before)
