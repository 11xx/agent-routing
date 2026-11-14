"""The guide: a bounded map printed by the bare command, and topics that carry the depth.

Bare `agent-routing` prints the map, which is short enough to be read whole.
`agent-routing guide` indexes the topics and prints one at a time; each topic
is bounded too. The text lives in doctrine/guide/.
"""

import argparse
import pathlib

#: The most lines and bytes the map may hold, and the most bytes one topic may
#: hold. A topic that outgrows its bound is split, never trimmed.
MAP_MAX_LINES = 80
MAP_MAX_BYTES = 6144
TOPIC_MAX_BYTES = 16384

#: The matching lines a search shows for one route before it only counts them.
SEARCH_CONTEXT_LINES = 3

#: Each group of the index: its title, then each topic's name and one-line summary.
GROUPS = (
    ("Before any query", (
        ("principles", "The three principles that bind every query"),
    )),
    ("Route work", (
        ("resolve", "Choosing a profile, resolving it, picker routes and the caller's seat"),
        ("validate", "Checking an exact tuple the operator named"),
        ("quota", "Admission against account windows before dispatch"),
        ("review", "Assessing a review, the capability ladder and the review frontier"),
    )),
    ("Read the policy", (
        ("views", "The verbs that print the policy, and the readable text views"),
        ("stores", "What each store under data/ holds and how it is validated"),
    )),
    ("Change the policy", (
        ("edit", "Every edit verb, what it writes and what it refuses"),
        ("notes", "Filing, repeating, retracting and reading field evidence"),
        ("page", "The local page that reads the stores and edits through the verbs"),
    )),
    ("For tools that read routing", (
        ("consumers", "The consumer lint, the price export and Claude agent emission"),
    )),
)

NAMES = tuple(name for _, topics in GROUPS for name, _ in topics)


def text_root(root: pathlib.Path) -> pathlib.Path:
    return root / "doctrine" / "guide"


def read(root: pathlib.Path, name: str) -> str:
    return (text_root(root) / f"{name}.txt").read_text(encoding="utf-8")


def index() -> str:
    lines = ["Guide topics, one at a time with `agent-routing guide <topic>`:"]
    for title, topics in GROUPS:
        lines += ["", title]
        lines += [f"  agent-routing guide {name:<11} {summary}" for name, summary in topics]
    lines += [
        "",
        "  agent-routing guide --search TEXT    The topics that mention TEXT.",
        "  agent-routing guide --all            Every topic at once: long, only when asked for.",
        "  agent-routing --help                 Every verb with its arguments.",
    ]
    return "\n".join(lines) + "\n"


def full(root: pathlib.Path) -> str:
    """Every topic, each exactly as it prints alone."""
    return "\n".join(read(root, name) for name in NAMES)


def search(root: pathlib.Path, needle: str) -> str:
    """The map and topics that hold `needle`, each with its first matching lines.

    The match is literal and ignores case. No topic's whole text is returned.
    """
    wanted = needle.lower()
    routes = [("agent-routing", read(root, "map"))]
    routes += [(f"agent-routing guide {name}", read(root, name)) for name in NAMES]
    out = []
    for command, text in routes:
        matching = [line.strip() for line in text.splitlines() if wanted in line.lower()]
        if not matching:
            continue
        out.append(command)
        out += [f"    {line}" for line in matching[:SEARCH_CONTEXT_LINES]]
        if len(matching) > SEARCH_CONTEXT_LINES:
            out.append(f"    … {len(matching) - SEARCH_CONTEXT_LINES} more matching lines")
    if not out:
        return f"No guide topic mentions `{needle}`. `agent-routing guide` lists the topics.\n"
    return "\n".join(out) + "\n"


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="agent-routing guide",
        description="Print the guide's topic index, or one topic. "
                    "Bare `agent-routing` prints the map that names the topics.",
    )
    command.add_argument("topic", nargs="?", choices=NAMES, metavar="TOPIC",
                         help="the topic to print: " + ", ".join(NAMES))
    selection = command.add_mutually_exclusive_group()
    selection.add_argument("--all", action="store_true",
                           help="every topic at once; long, so ask only when one topic "
                                "at a time will not do")
    selection.add_argument("--search", metavar="TEXT",
                           help="list the topics that mention TEXT, literally and ignoring "
                                "case; write --search=TEXT when TEXT starts with a dash")
    selection.add_argument("--map", action="store_true", help=argparse.SUPPRESS)
    return command


def main(root: pathlib.Path, argv: list[str]) -> str:
    """What `agent-routing guide ARGV` prints. A misuse exits 2 through argparse."""
    command = parser()
    args = command.parse_args(argv)
    if args.topic is not None and (args.all or args.search is not None or args.map):
        command.error("give a topic, --all or --search, not two of them")
    if args.map:
        return read(root, "map")
    if args.search is not None:
        return search(root, args.search)
    if args.all:
        return full(root)
    if args.topic is None:
        return index()
    return read(root, args.topic)
