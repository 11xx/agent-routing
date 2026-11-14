"""Argument and output adapters for the store-edit library."""

import argparse
import json

import data_edits
import field_notes
import stores

EDITS = ("set-seat", "remove-seat", "default-seat", "prohibit", "allow", "rank", "set-fallback", "remove-fallback",
         "set-guard", "retire-guard", "add-model", "supersede-model", "note", "again", "retract", "supersede", "commit", "undo")


def parser():
    root = argparse.ArgumentParser(prog="agent-routing", description=__doc__)
    commands = root.add_subparsers(dest="verb", required=True)
    for verb in (*EDITS, "notes", "card", "log"):
        p = commands.add_parser(verb)
        p.add_argument("--json", action="store_true")
        if verb in EDITS:
            p.add_argument("--dry-run", action="store_true")
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
            p.add_argument("--when", required=True)
        if verb in {"prohibit", "allow", "rank", "set-guard", "retire-guard", "add-model", "supersede-model", "card"}:
            p.add_argument("model")
        if verb in {"prohibit", "allow", "rank"}:
            p.add_argument("effort")
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
        if verb in {"note", "again", "retract", "supersede"}:
            p.add_argument("--date")
        if verb == "notes":
            p.add_argument("model", nargs="?")
            p.add_argument("--kind", choices=stores.NOTE_KINDS)
            p.add_argument("--area")
            p.add_argument("--liveness", choices=("live", "inactive", "all"), default="live")
        if verb == "log":
            p.add_argument("--limit", type=int, default=20)
    return root


def main(root, argv=None):
    args = vars(parser().parse_args(argv))
    verb, as_json = args.pop("verb"), args.pop("json")
    try:
        if verb == "log":
            if args["limit"] < 1:
                raise stores.StoreError("--limit must be positive")
            result = dict(schema="agent-routing-history/1", edits=data_edits.history(root, **args))
            text = "\n".join(f"{row['commit'][:12]} {row['subject']}" for row in result["edits"])
        elif verb in {"notes", "card"}:
            with stores.store_lock(root, exclusive=False):
                texts = data_edits.read_texts(root)
            data_edits.checked(texts)
            records = stores.parse_notes(texts[stores.NOTES])
            if verb == "notes":
                result = dict(schema="agent-routing-notes/1", notes=field_notes.select(records, **args))
            else:
                result = dict(schema="agent-routing-card/1",
                              **field_notes.card(stores.Data.from_texts(texts), records, args["model"]))
            text = data_edits.render(result)
        else:
            result = data_edits.apply(root, verb, **args)
            text = data_edits.render(result)
        print(json.dumps(result, ensure_ascii=False) if as_json else text)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        if as_json:
            print(json.dumps(dict(schema="agent-routing-edit-error/1", verb=verb, error=str(error))))
        else:
            import sys
            print(f"agent-routing: {error}", file=sys.stderr)
        return 1
