"""On-demand faulty variants for edit acceptance claims; never part of the change gate.

Run: python3 tests/probe_edits.py
Each probe first runs the named test with one faulty production behavior,
requires the predicted failure, then runs the unchanged test against the head.
The fixture owns every Git repository it edits.
"""

import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_edits import EditTest
from test_edit_cli import EditCliTest
from test_notes import NoteTest
from test_note_records import NoteRecordsTest
import data_edits
import edit_cli
import field_notes


def git_variant(transform):
    real = data_edits.git
    def altered(root, *args, **opts):
        replacement = transform(args)
        return replacement if isinstance(replacement, bytes) else real(root, *replacement, **opts)
    return patch.object(data_edits, "git", side_effect=altered)


def dry_variant():
    real = data_edits.apply
    def writing(root, verb, **opts):
        return real(root, verb, **{**opts, "dry_run": False})
    return patch.object(data_edits, "apply", side_effect=writing)


def truncate_variant():
    real = data_edits.atomic_write
    def truncate(path, text):
        path.write_text(text[:len(text) // 2])
        return real(path, text)
    return patch.object(data_edits, "atomic_write", side_effect=truncate)


def note_order_variant():
    real = field_notes.project
    return patch.object(field_notes, "project", side_effect=lambda rows: sorted(real(rows), key=lambda row: row["id"], reverse=True))


def live_variant():
    real = field_notes.project
    def all_live(rows):
        result = real(rows)
        for row in result:
            row["live"] = True
        return result
    return patch.object(field_notes, "project", side_effect=all_live)


def inherited_variant():
    real = field_notes.card
    def omitted(*args):
        result = real(*args)
        result["inherited_unverified"] = []
        return result
    return patch.object(field_notes, "card", side_effect=omitted)


def text_variant():
    real = data_edits.render
    def omitted(result):
        result = dict(result)
        result["old_route_version"] = "omitted"
        return real(result)
    return patch.object(data_edits, "render", side_effect=omitted)


def net_growth_variant():
    return patch.object(data_edits, "notes_history_problems", return_value=[])


def rollback_variant():
    real = data_edits.atomic_write
    calls = 0
    def no_rollback(path, text):
        nonlocal calls
        calls += 1
        if calls == 1:
            real(path, text)
    return patch.object(data_edits, "atomic_write", side_effect=no_rollback)


def no_default_variant():
    real = data_edits.change_rows
    def ignored(catalog, policy, verb, opts, today):
        if verb != "default-seat":
            real(catalog, policy, verb, opts, today)
    return patch.object(data_edits, "change_rows", side_effect=ignored)


def discard_primary_variant():
    real = data_edits.change_rows
    def discarded(catalog, policy, verb, opts, today):
        real(catalog, policy, verb, opts, today)
        if verb == "default-seat":
            policy["seat"] = [row for row in policy["seat"] if not row.get("variant", "").startswith("primary-")]
    return patch.object(data_edits, "change_rows", side_effect=discarded)


def ignore_filters_variant():
    real = field_notes.select
    return patch.object(field_notes, "select", side_effect=lambda rows, **opts: real(rows))


def no_compensation_variant():
    return patch.object(field_notes, "active_records", side_effect=lambda rows: [row for row in rows if row.get("event") != "undo"])


def null_correction_variant():
    real = data_edits.change_notes
    def nulled(records, verb, opts, today):
        result = real(records, verb, opts, today)
        if verb == "supersede":
            records[-2]["model"] = None
        return result
    return patch.object(data_edits, "change_notes", side_effect=nulled)


def json_banner_variant():
    real = edit_cli.main
    def banner(*args):
        print("edit banner")
        return real(*args)
    return patch.object(edit_cli, "main", side_effect=banner)


PROBES = [
    (EditTest, "test_refusal_atomic", lambda: patch.object(data_edits, "candidate_problems", return_value=[]), "not raised", "invalid candidates accepted"),
    (EditTest, "test_accepted_edit_is_one_canonical_row_and_data_commit",
     lambda: git_variant(lambda args: tuple("--include" if arg == "--only" else arg for arg in args)),
     "unrelated.txt", "unrelated staged work included"),
    (EditTest, "test_reader_between_lock_and_rename", truncate_variant, "AssertionError", "destination truncated before rename"),
    (EditTest, "test_dirty_refuses", lambda: git_variant(lambda args: b"" if args[0] == "status" else args), "not raised", "dirty stores ignored"),
    (EditTest, "test_dry_run_writes_nothing", dry_variant, "False is not true", "dry-run flag ignored"),
    (EditTest, "test_undo_restores_bytes_and_answers", lambda: patch.object(data_edits, "merge_revert", side_effect=lambda current, *args: current),
     "edit makes no change", "undo omits the inverse"),
    (NoteTest, "test_ids_append_one_line", lambda: patch.object(field_notes, "next_id", return_value="n0003"),
     "id is used twice", "note id reused"),
    (NoteTest, "test_again_changes_card_order", note_order_variant, "n0001", "recency replaces recurrence ordering"),
    (NoteTest, "test_events", live_variant, "n0002", "dispositions leave old notes live"),
    (NoteTest, "test_growth_rejects_earlier_changes", lambda: patch.object(field_notes, "grows_only", return_value=[]),
     "rewritten prefix was accepted", "growth check accepts changed prefix"),
    (NoteTest, "test_history_catches_a_rewrite_hidden_by_restoration", net_growth_variant,
     "[] is not true", "only net history checked"),
    (NoteTest, "test_card_marks_inheritance", inherited_variant, "n0001", "predecessor evidence omitted"),
    (EditTest, "test_json_matches_text_facts", text_variant, "omitted", "text drops the old route version"),
    (NoteRecordsTest, "test_lifecycle", lambda: patch.object(field_notes, "select", return_value=[]),
     "n0001", "event projection omits live recurrence"),
    (EditTest, "test_commit_hand_edits_and_reject_notes_rewrite", lambda: patch.object(field_notes, "grows_only", return_value=[]),
     "not raised", "hand commit rewrites earlier notes"),
    (EditTest, "test_commit_failure_rolls_back", rollback_variant, "AssertionError", "failed commit leaves applied bytes"),
    (EditTest, "test_default_fallback_guard_and_catalog", no_default_variant, "edit makes no change", "default edit is a no-op"),
    (EditTest, "test_undo_conflict_and_disjoint_later_hand_edit",
     lambda: patch.object(data_edits, "merge_revert", side_effect=lambda current, edited, previous, name: previous),
     "scoped survey", "undo discards disjoint later edits"),
    (EditTest, "test_promote_variant_retains_primary", discard_primary_variant, "primary-codex", "promotion deletes the primary seat"),
    (EditTest, "test_removing_default_refuses", lambda: patch.object(data_edits, "default_problems", return_value=[]),
     "not raised", "default coverage is unchecked"),
    (NoteTest, "test_filters_and_event_validation", ignore_filters_variant, "3 != 2", "note filters ignored"),
    (NoteTest, "test_undo_note_appends_compensation", no_compensation_variant, "n0001", "compensating records ignored"),
    (EditCliTest, "test_note_correction_keeps_omitted_fields", null_correction_variant, "model must", "omitted CLI fields become null"),
    (EditCliTest, "test_wrapper_and_json_refusal", json_banner_variant, "JSONDecodeError", "wrapper prefixes JSON with a banner"),
    (EditCliTest, "test_attribution_comes_only_from_arc_env", lambda: patch.object(data_edits, "attribution", return_value="fixture:invented#high"),
     "is not None", "missing acting model is guessed"),
]


def run(cls, name):
    out = io.StringIO()
    result = unittest.TextTestRunner(stream=out, verbosity=2).run(unittest.TestSuite([cls(name)]))
    return result, out.getvalue()


def main():
    report = []
    for cls, name, variant, expected, fault in PROBES:
        with variant():
            broken, output = run(cls, name)
        if broken.wasSuccessful() or expected not in output:
            print(output, file=sys.stderr)
            raise SystemExit(f"probe did not reject the predicted fault: {fault}")
        clean, output = run(cls, name)
        if not clean.wasSuccessful():
            print(output, file=sys.stderr)
            raise SystemExit(f"head failed: {name}")
        row = dict(test=f"{cls.__module__}.{cls.__name__}.{name}", fault=fault, predicted=expected,
                   faulty="fail", head="pass")
        report.append(row)
        print(json.dumps(row), flush=True)
    print(f"{len(report)} faulty variants rejected; {len(report)} restored tests passed")


if __name__ == "__main__":
    main()
