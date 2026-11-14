"""Append-only field evidence and its current, recurrence-ordered projection."""

import copy
import re

import stores

EVENTS = ("again", "retract", "supersede", "undo")


def next_id(records):
    return f"n{1 + max((int(row['id'][1:]) for row in records), default=0):04d}"


def active_records(records):
    disabled = set()
    active = []
    for row in reversed(records):
        if row["id"] in disabled:
            continue
        if row.get("event") == "undo":
            disabled.add(row["note"])
        else:
            active.append(row)
    return list(reversed(active))


def project(records):
    """Notes with liveness, occurrence dates and evidence, ordered by recurrence and recency."""
    notes = {}
    for row in active_records(records):
        event = row.get("event")
        if event is None:
            notes[row["id"]] = dict(copy.deepcopy(row), live=True, occurrences=1, last_seen=row["date"],
                                    evidence=[{"date": row["date"], "reference": row["evidence"]}])
        elif row["note"] in notes:
            note = notes[row["note"]]
            if event == "again":
                note["occurrences"] += 1
                note["last_seen"] = max(note["last_seen"], row["date"])
                note["evidence"].append({"date": row["date"], "reference": row["evidence"]})
            else:
                note["live"] = False
                note["disposition"] = copy.deepcopy(row)
    return sorted(notes.values(), key=lambda row: (row["occurrences"], row["last_seen"], row["id"]), reverse=True)


def problems(records, catalog):
    errors, prior, previous = [], {}, 0
    for row in records:
        where = f"{stores.NOTES} note {row.get('id')!r}"
        spec = stores.EVENT_KEYS if "event" in row else stores.NOTE_KEYS
        shape = stores._key_problems(where, spec, row)
        errors += shape
        if shape:
            continue
        number = int(row["id"][1:]) if re.fullmatch(r"n[0-9]{4,}", row["id"]) else None
        if number is None:
            errors.append(f"{where}: id must be n followed by at least four digits")
        elif number <= previous:
            errors.append(f"{where}: ids increase down the file")
        previous = number or previous
        if row["id"] in prior:
            errors.append(f"{where}: id is used twice")
        if "event" not in row:
            errors += [error for error in stores._note_problems([row], catalog)
                       if "id must be" not in error]
            if len(row["claim"]) > 1000 or re.search(r"[.!?]\s+[A-Z]", row["claim"]):
                errors.append(f"{where}: claim must be one sentence of at most 1000 characters")
            tiers = stores._keys(catalog, "tier", "model", "effort")
            if "effort" in row and (row["model"], row["effort"]) not in tiers:
                errors.append(f"{where}: effort is not a tier of its model")
        else:
            event = row["event"]
            target = prior.get(row["note"])
            if event not in EVENTS:
                errors.append(f"{where}: event must be one of {', '.join(EVENTS)}")
            if target is None or (event != "undo" and "event" in target):
                errors.append(f"{where}: note must name an earlier {'record' if event == 'undo' else 'note'}")
            required = ("evidence",) if event == "again" else ("reason", "replacement") if event == "supersede" else ("reason",)
            allowed = {"id", "date", "event", "note", *required}
            for key in required:
                if key not in row:
                    errors.append(f"{where}: {key} is required for {event}")
            for key in row.keys() - allowed:
                errors.append(f"{where}: {key} does not belong to {event}")
            if event == "supersede" and "replacement" in row:
                replacement = prior.get(row["replacement"])
                if replacement is None or "event" in replacement or row["replacement"] == row["note"]:
                    errors.append(f"{where}: replacement must name a different earlier note")
            if target is not None and event != "undo" and not errors:
                live = {note["id"] for note in project(list(prior.values())) if note["live"]}
                if row["note"] not in live:
                    errors.append(f"{where}: note is not live")
        prior[row["id"]] = row
    return errors


def grows_only(before, after):
    """Only complete lines may be appended; an earlier byte cannot change."""
    if not after.startswith(before) or (before and not before.endswith(b"\n")):
        return [f"{stores.NOTES}: append-only history changed an earlier line or removed bytes"]
    return []


def select(records, *, model=None, kind=None, area=None, liveness="live"):
    return [row for row in project(records) if (model is None or row["model"] == model)
            and (kind is None or row["kind"] == kind) and (area is None or area in row["areas"])
            and (liveness == "all" or row["live"] == (liveness == "live"))]


def card(data, records, model):
    if model not in data.by_model():
        raise stores.StoreError(f"{stores.CATALOG} [[model]] id={model}: no such model")
    predecessors = {row["id"] for row in data.catalog.get("model", []) if row.get("successor") == model}
    return {"model": model,
            "seats": [row for row in data.policy.get("seat", []) if row["model"] == model],
            "prohibited": [row for row in data.catalog.get("tier", [])
                           if row["model"] == model and row.get("prohibited")],
            "guards": [row for row in data.policy.get("guard", []) if row["model"] == model],
            "notes": select(records, model=model),
            "inherited_unverified": [row for row in select(records) if row["model"] in predecessors]}
