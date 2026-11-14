"""Argument and output adapters for the store-edit library."""

import argparse
import json

import data_edits
import field_notes
import stores

EDITS = ("set-seat", "remove-seat", "default-seat", "prohibit", "allow", "rank", "pool-rank", "set-fallback", "remove-fallback",
         "set-review-seat", "remove-review-seat", "set-guard", "retire-guard", "add-model", "supersede-model", "note", "again", "retract", "supersede", "commit", "undo")


class UsageError(ValueError):
    """Arguments the verb's parser refuses, in the parser's own words."""


class RaisingParser(argparse.ArgumentParser):
    """The verbs' parser for an in-process caller: a refusal raises instead of printing and exiting."""

    def error(self, message):
        raise UsageError(message)

    def exit(self, status=0, message=None):
        raise UsageError((message or "").strip() or f"{self.prog}: no result")

    def print_help(self, file=None):
        pass

    def print_usage(self, file=None):
        pass


def parser(*, raising=False):
    root = (RaisingParser if raising else argparse.ArgumentParser)(prog="agent-routing", description=__doc__)
    commands = root.add_subparsers(dest="verb", required=True)
    for verb in (*EDITS, "notes", "card", "log"):
        p = commands.add_parser(verb)
        p.add_argument("--json", action="store_true")
        if verb in EDITS:
            p.add_argument("--dry-run", action="store_true")
            p.add_argument("--expect", metavar="STATE",
                           help="refuse unless the stores and their edit history are in this state, a preview's `state`")
            if verb != "commit":
                p.add_argument("--date", metavar="YYYY-MM-DD",
                               help="the date the edit records (a seat's or guard's since, a note's date); today if omitted")
            if verb not in {"note", "again", "retract", "supersede"}:
                p.add_argument("--why", required=True)
                p.add_argument("--because", action="append", default=[])
        if verb in {"set-seat", "remove-seat", "default-seat", "set-fallback", "remove-fallback"}:
            p.add_argument("profile")
            p.add_argument("--variant")
        if verb in {"set-seat", "default-seat"}:
            p.add_argument("--backend", action="append", required=verb == "set-seat")
        if verb == "set-seat":
            p.add_argument("--model", required=True)
            p.add_argument("--effort", required=True)
            p.add_argument("--provider")
            p.add_argument("--stability", choices=stores.SEAT_STABILITIES)
            p.add_argument("--pool-rank", type=int,
                           help="the seat's tier's place in its pool's order; needed when that tier is unranked there")
            p.add_argument("--when", required=True)
        if verb in {"set-review-seat", "remove-review-seat"}:
            p.add_argument("purpose", choices=stores.REVIEW_PURPOSES)
            p.add_argument("--author-family", required=True,
                           help=f"the author lab the seat serves: a catalog family id or {stores.ANY_FAMILY}")
            p.add_argument("--backend", required=True)
        if verb == "set-review-seat":
            p.add_argument("--model", required=True)
            p.add_argument("--effort", required=True)
            p.add_argument("--when", required=True)
        if verb in {"prohibit", "allow", "rank", "pool-rank", "set-guard", "retire-guard", "add-model", "supersede-model",
                    "card"}:
            p.add_argument("model")
        if verb in {"prohibit", "allow", "rank", "pool-rank"}:
            p.add_argument("effort")
        if verb == "pool-rank":
            p.add_argument("--pool", required=True, help="the provider whose pool the rank orders")
            p.add_argument("--rank", type=int, required=True)
        if verb == "prohibit":
            p.add_argument("--reason", required=True)
        if verb == "rank":
            p.add_argument("--rank", type=int, required=True)
            p.add_argument("--floor", type=int, required=True)
        if verb in {"set-fallback", "remove-fallback"}:
            p.add_argument("--from-provider", required=True)
            p.add_argument("--backend", required=True)
        if verb in {"set-guard", "retire-guard"}:
            p.add_argument("--effort")
            p.add_argument("--profile")
            if verb == "set-guard":
                p.add_argument("--rule", required=True)
        if verb == "add-model":
            p.add_argument("--family", required=True)
            p.add_argument("--reach", action="append", type=json.loads, required=True,
                           help='JSON row: {"backend":"...","provider":"...","backend_model":"..."}')
            p.add_argument("--tier", action="append", type=json.loads, required=True,
                           help='JSON row: {"effort":"...","rank":1,"floor":1}')
        if verb == "supersede-model":
            p.add_argument("--successor", required=True)
        if verb in {"note", "supersede"}:
            p.add_argument("--model", required=verb == "note")
            p.add_argument("--effort")
            p.add_argument("--kind", choices=stores.NOTE_KINDS, required=verb == "note")
            p.add_argument("--area", dest="areas", action="append", required=verb == "note")
            p.add_argument("--claim", required=True)
            p.add_argument("--cause", choices=stores.NOTE_CAUSES, required=verb == "note")
            p.add_argument("--metrics", type=json.loads)
        if verb in {"again", "retract", "supersede"}:
            p.add_argument("note")
        if verb in {"note", "again", "supersede"}:
            p.add_argument("--evidence", required=True)
        if verb in {"retract", "supersede"}:
            p.add_argument("--reason", required=True)
        if verb == "notes":
            p.add_argument("model", nargs="?")
            p.add_argument("--kind", choices=stores.NOTE_KINDS)
            p.add_argument("--area")
            p.add_argument("--liveness", choices=("live", "inactive", "all"), default="live")
        if verb == "log":
            p.add_argument("--limit", type=int, default=20)
        if verb == "undo":
            p.add_argument("--commit", dest="target", metavar="REV",
                           help="refuse unless REV is the latest verb edit, the one a preview named")
    return root


def arguments(argv, *, raising=False):
    """A verb, whether it asked for JSON, and the options its library call takes."""
    args = vars(parser(raising=raising).parse_args(argv))
    return args.pop("verb"), args.pop("json"), args


def execute(root, verb, args):
    """The result object the verb prints with --json, and the data a card or notes view read it from."""
    if verb == "log":
        if args["limit"] < 1:
            raise stores.StoreError("--limit must be positive")
        return dict(schema="agent-routing-history/1", edits=data_edits.history(root, **args)), None
    if verb in {"notes", "card"}:
        with stores.store_lock(root, exclusive=False):
            texts = data_edits.read_texts(root)
        data_edits.checked(texts)
        records = stores.parse_notes(texts[stores.NOTES])
        loaded = stores.Data.from_texts(texts)
        if verb == "notes":
            return dict(schema="agent-routing-notes/1", notes=field_notes.select(records, **args)), loaded
        return dict(schema="agent-routing-card/1", **field_notes.card(loaded, records, args["model"])), loaded
    return data_edits.apply(root, verb, **args), None


def main(root, argv=None):
    verb, as_json, args = arguments(argv)
    try:
        result, loaded = execute(root, verb, args)
        if as_json:
            text = None
        elif verb == "log":
            text = data_edits.render(result, root=root)
        elif verb in {"notes", "card"}:
            text = data_edits.render(result, data=loaded)
        else:
            text = data_edits.render(result)
        print(json.dumps(result, ensure_ascii=False) if as_json else text)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        if as_json:
            print(json.dumps(dict(schema="agent-routing-edit-error/1", verb=verb, error=str(error),
                                  **({"stale": True} if isinstance(error, data_edits.StaleState) else {}))))
        else:
            import sys
            print(f"agent-routing: {error}", file=sys.stderr)
        return 1
