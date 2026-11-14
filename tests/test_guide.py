"""The guide: a bounded map bare, bounded topics behind it, and the routes between them."""

import re
import subprocess
import unittest

from fixture import REPOSITORY, ROOT, run_command

import guide


def routing_guide(*argv):
    return run_command(ROOT / "bin" / "routing-guide", list(argv))


class MapTest(unittest.TestCase):
    def test_the_bare_command_prints_a_map_that_fits_one_reading(self):
        """Claim: bare `agent-routing` prints the map, within its line and
        byte ceilings, and its opening says it is whole and where the depth
        is. Rejects a guide so long that a reader cuts it with `head` and
        never learns what the rest held."""
        done = subprocess.run([str(REPOSITORY / "bin" / "agent-routing")], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)
        text = done.stdout
        self.assertEqual(text, guide.read(REPOSITORY, "map"))
        self.assertLessEqual(len(text.splitlines()), guide.MAP_MAX_LINES)
        self.assertLessEqual(len(text.encode()), guide.MAP_MAX_BYTES)
        opening = "\n".join(text.splitlines()[:8])
        for phrase in ("read all of it", "`agent-routing guide`", "--help"):
            self.assertIn(phrase, opening)

    def test_the_map_and_the_index_name_every_topic_and_only_topics(self):
        """Claim: every topic is named by a `Topics:` line of the map and by
        the index, and neither names anything else. Rejects a topic no reader
        can discover, and a route that names no topic."""
        named = set()
        for line in guide.read(REPOSITORY, "map").splitlines():
            if line.strip().startswith("Topics:"):
                named.update(line.split(":", 1)[1].split())
        self.assertEqual(named, set(guide.NAMES))
        code, out, _ = routing_guide()
        self.assertEqual(code, 0)
        indexed = {line.split()[2] for line in out.splitlines()
                   if line.startswith("  agent-routing guide ") and not line.split()[2].startswith("-")}
        self.assertEqual(indexed, set(guide.NAMES))


class TopicTest(unittest.TestCase):
    def test_every_topic_prints_within_its_bound(self):
        """Claim: `guide <topic>` prints that topic alone, at most
        TOPIC_MAX_BYTES. Rejects a topic grown into a manual of its own."""
        for name in guide.NAMES:
            with self.subTest(topic=name):
                code, out, _ = routing_guide(name)
                self.assertEqual(code, 0)
                self.assertTrue(out.endswith("\n"))
                self.assertLessEqual(len(out.encode()), guide.TOPIC_MAX_BYTES)
                self.assertEqual(out, guide.read(ROOT, name))

    def test_the_whole_guide_holds_every_topic_unaltered(self):
        """Claim: `guide --all` holds each topic exactly as it prints alone.
        Rejects a full print that drops or alters one."""
        code, whole, _ = routing_guide("--all")
        self.assertEqual(code, 0)
        for name in guide.NAMES:
            self.assertIn(guide.read(ROOT, name), whole)

    def test_every_cross_reference_names_a_topic(self):
        """Claim: a `agent-routing guide NAME` reference in the map or a topic
        names a topic. Rejects one left pointing at a renamed topic."""
        text = guide.read(REPOSITORY, "map") + guide.full(REPOSITORY)
        for name in re.findall(r"`agent-routing guide ([a-z][a-z-]*)`", text):
            self.assertIn(name, guide.NAMES)

    def test_an_unknown_topic_and_a_combined_selection_are_usage_errors(self):
        """Claim: an unknown topic exits 2 with nothing on stdout and the
        topic names on stderr; a topic with --all or --search exits 2.
        Rejects a silent empty answer and a dump of the whole guide."""
        code, out, err = routing_guide("no-such-topic")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("principles", err)
        for argv in (["edit", "--all"], ["edit", "--search", "seat"], ["--all", "--search", "seat"]):
            with self.subTest(argv=argv):
                self.assertEqual(routing_guide(*argv)[0], 2)


class SearchTest(unittest.TestCase):
    def test_search_lists_routes_without_printing_them_whole(self):
        """Claim: `guide --search TEXT` matches whatever the case and answers
        with each matching route and a few of its lines. Rejects a search
        that answers with a matching topic printed whole."""
        code, found, _ = routing_guide("--search", "POOL RANK")
        self.assertEqual(code, 0)
        self.assertIn("agent-routing guide edit\n", found)
        self.assertIn("more matching lines", found)
        self.assertNotIn(guide.read(ROOT, "edit"), found)
        code, nothing, _ = routing_guide("--search", "zzz-no-such-text-zzz")
        self.assertEqual(code, 0)
        self.assertIn("`agent-routing guide` lists the topics", nothing)


if __name__ == "__main__":
    unittest.main()
