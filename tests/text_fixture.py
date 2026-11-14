"""Invented records covering the human views without changing the stored roster fixture."""

import copy
import pathlib

from fixture import FIXTURE
import field_notes
import stores


def sample():
    original = stores.load(FIXTURE)
    catalog, policy = copy.deepcopy(original.catalog), copy.deepcopy(original.policy)
    policy["seat"].append(dict(profile="implement", variant="bounded", backends=["claude"], provider="northwind-plan",
                               model="nw-atlas-2", effort="medium", stability="experimental",
                               when="Explicit comparison with a fixed deadline.", why="Measure the bounded trial.", since="2030-01-06"))
    policy["guard"].append(dict(model="nw-atlas-2", effort="high", profile="implement",
                                rule="Name exact targets and stop when a target is absent before beginning any implementation.",
                                why="The fixture's failed brief left its target ambiguous.", since="2030-01-06", because=["n0003"]))
    records = stores.load_notes(FIXTURE)
    def note(number, model, kind, claim, date="2030-01-06", effort="high"):
        records.append(dict(id=f"n{number:04d}", date=date, model=model, effort=effort, kind=kind,
                            areas=["implementation"], claim=claim, cause="executor", evidence=f"fixture:case-{number}"))
    note(3, "nw-atlas-2", "weakness", "An ambiguous target can send implementation past the intended files unless the brief names a stop condition.")
    records.append(dict(id="n0004", date="2030-01-09", event="again", note="n0003", evidence="fixture:repeat"))
    note(5, "nw-atlas-2", "strength", "A bounded change with named probes lands cleanly.", "2030-01-07")
    note(6, "nw-atlas-1", "observation", "The predecessor needed explicit target boundaries.", "2030-01-03")
    note(7, "nw-atlas-2", "measurement", "A fixture board records a partial score.", "2030-01-08")
    note(8, "nw-atlas-2", "weakness", "The first record attributed the wrong executor.", "2030-01-08")
    records.append(dict(id="n0009", date="2030-01-09", event="retract", note="n0008", reason="The executor was misidentified."))
    note(10, "nw-atlas-2", "measurement", "The corrected fixture score is one quarter.", "2030-01-09")
    records[-1]["metrics"] = {"pass_at_1": 0.25}
    records.append(dict(id="n0011", date="2030-01-09", event="supersede", note="n0007", replacement="n0010",
                        reason="The original score was misread."))
    return stores.Data(catalog, policy, "fixture"), records


def card_result():
    data, records = sample()
    return data, dict(schema="agent-routing-card/1", **field_notes.card(data, records, "nw-atlas-2"))


def write(root):
    data, records = sample()
    texts = {stores.CATALOG: stores.emit_catalog(data.catalog), stores.POLICY: stores.emit_policy(data.policy),
             stores.NOTES: stores.emit_notes(records)}
    for name, text in texts.items():
        (pathlib.Path(root) / name).write_text(text)
    return texts
